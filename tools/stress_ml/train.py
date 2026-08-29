#!/usr/bin/env python
"""
Навучанне мадэлі пастаноўкі націску (StressML_model) на tools/stress_ml/stress.list.

Патрабуе ўсталяваны пакет BelVoice (для агульнай архітэктуры мадэлі) і асобна
ўсталяваныя torch/safetensors (гл. tools/stress_ml/requirements.txt):

    pip install -e /home/alex/gits/BelVoice
    pip install -r tools/stress_ml/requirements.txt

Прыклад запуску:
    python tools/stress_ml/train.py --stress-list tools/stress_ml/stress.list

Пасля навучання вагі (stress_ml.safetensors) і канфіг/слоўнік (stress_ml_config.json)
захоўваюцца напрамую ў framework/belvoice/synth/stress/, адкуль іх падхоплівае клас
StressML. Гл. tools/stress_ml/README.md для апісання ідэі і архітэктуры.
"""
import argparse
import copy
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from safetensors.torch import save_file
from torch.utils.data import DataLoader, WeightedRandomSampler

from data import build_corpus, StressDataset, make_collate_fn, VOWELS, is_nontrivial
from model import StressML_model, UNK_ID

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = HERE.parent.parent / "framework" / "belvoice" / "synth" / "stress"


@dataclass
class EvalResult:
    n: int
    acc: float
    acc_nontrivial: float
    n_nontrivial: int
    confidences: list[tuple[float, bool]]


@dataclass
class HomographEvalResult:
    n: int
    top1: float
    topk: float


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stress-list", default=str(HERE / "stress.list"))
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--cache", default=str(HERE / ".corpus_cache.pkl"))
    p.add_argument("--rebuild-cache", action="store_true")
    p.add_argument("--max-lines", type=int, default=None, help="для хуткага smoke-тэсту на частцы дадзеных")

    p.add_argument("--val-ratio", type=float, default=0.05)
    p.add_argument("--test-ratio", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=42)

    p.add_argument("--d-model", type=int, default=256)
    p.add_argument("--n-layers", type=int, default=6)
    p.add_argument("--n-heads", type=int, default=8)
    p.add_argument("--dropout", type=float, default=0.15)
    p.add_argument("--max-len", type=int, default=48)

    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=768)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight-decay", type=float, default=0.01)
    p.add_argument("--warmup-ratio", type=float, default=0.02)
    p.add_argument("--label-smoothing", type=float, default=0.1)
    p.add_argument("--ema-decay", type=float, default=0.999)
    p.add_argument("--patience", type=int, default=5, help="early stopping, у эпохах без паляпшэння")

    p.add_argument("--aug-prob", type=float, default=0.3)
    p.add_argument("--unk-dropout", type=float, default=0.01)

    p.add_argument("--confidence-threshold", type=float, default=0.9)
    p.add_argument("--num-workers", type=int, default=2)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def masked_label_smoothing_loss(logits, targets, vowel_mask, smoothing: float = 0.1):
    """
    Cross-entropy з label smoothing, размеркаваным толькі па сапраўдных
    (галосных) пазіцыях кожнага прыкладу. Звычайны
    `F.cross_entropy(..., label_smoothing=...)` размяркоўвае smoothing-масу па
    ЎСІХ класах, уключна з замаскіраванымі (-1e4) пазіцыямі, што штучна раздувае
    loss (масавае сумаванне вялікіх -log_softmax па замаскіраваных класах).
    """
    log_probs = F.log_softmax(logits, dim=-1)
    with torch.no_grad():
        n_valid = vowel_mask.sum(dim=-1, keepdim=True).clamp(min=1).float()
        true_dist = torch.zeros_like(log_probs)
        true_dist.scatter_(1, targets.unsqueeze(1), 1.0 - smoothing)
        true_dist += (vowel_mask.float() / n_valid) * smoothing
    return -(true_dist * log_probs).sum(dim=-1)


@torch.no_grad()
def update_ema(ema_model: torch.nn.Module, model: torch.nn.Module, decay: float):
    for ema_t, t in zip(ema_model.state_dict().values(), model.state_dict().values()):
        if ema_t.dtype.is_floating_point:
            ema_t.mul_(decay).add_(t.detach(), alpha=1 - decay)
        else:
            ema_t.copy_(t)


def build_scheduler(optimizer, total_steps: int, warmup_steps: int):
    def lr_lambda(step):
        if step < warmup_steps:
            return (step + 1) / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return 0.5 * (1 + math.cos(math.pi * min(1.0, progress)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


@torch.no_grad()
def predict_batch(model, plains: list[str], char2id: dict, max_len: int, device: str, batch_size: int = 512):
    """Бацавы inference для адвольных сегментаў (без вядомага target). Вяртае
    для кожнага plain: (прадказаны індэкс у plain, упэўненасць, поўны tensor prob па пазіцыях plain)."""
    model.eval()
    results = []
    for start in range(0, len(plains), batch_size):
        chunk = plains[start:start + batch_size]
        L = min(max(len(p) for p in chunk), max_len)
        ids_batch, vowel_batch, pad_batch, shifts = [], [], [], []
        for plain in chunk:
            ids = [char2id.get(c, UNK_ID) for c in plain]
            vmask = [c in VOWELS for c in plain]
            clipped_ids = ids[-L:]
            clipped_vmask = vmask[-L:]
            offset = len(ids) - len(clipped_ids)  # колькі сімвалаў абрэзана з пачатку
            pad = L - len(clipped_ids)
            ids_batch.append([0] * pad + clipped_ids)
            vowel_batch.append([False] * pad + clipped_vmask)
            pad_batch.append([True] * pad + [False] * len(clipped_ids))
            shifts.append(offset - pad)  # idx_in_plain = pred_in_padded + shift
        ids_t = torch.tensor(ids_batch, dtype=torch.long, device=device)
        pad_t = torch.tensor(pad_batch, dtype=torch.bool, device=device)
        vowel_t = torch.tensor(vowel_batch, dtype=torch.bool, device=device)
        logits = model(ids_t, pad_t, vowel_t)
        probs = torch.softmax(logits, dim=-1)
        pred_idx = torch.argmax(probs, dim=-1)
        for i in range(len(chunk)):
            pred = int(pred_idx[i].item()) + shifts[i]
            conf = float(probs[i, pred_idx[i]].item())
            results.append((pred, conf, probs[i].detach().cpu()))
    return results


def evaluate(model, examples, char2id, max_len, device) -> EvalResult:
    if not examples:
        return EvalResult(n=0, acc=0.0, acc_nontrivial=float("nan"), n_nontrivial=0, confidences=[])
    plains = [ex.plain for ex in examples]
    preds = predict_batch(model, plains, char2id, max_len, device)
    correct = correct_nt = total_nt = 0
    confidences = []
    for ex, (pred, conf, _) in zip(examples, preds):
        hit = pred == ex.stress_index
        correct += hit
        if is_nontrivial(ex.plain):
            total_nt += 1
            correct_nt += hit
        confidences.append((conf, hit))
    n = len(examples)
    return EvalResult(
        n=n,
        acc=correct / n,
        acc_nontrivial=(correct_nt / total_nt) if total_nt else float("nan"),
        n_nontrivial=total_nt,
        confidences=confidences,
    )


def confidence_at_threshold(confidences, threshold: float):
    kept = [(c, h) for c, h in confidences if c >= threshold]
    coverage = len(kept) / len(confidences) if confidences else 0.0
    acc = sum(h for _, h in kept) / len(kept) if kept else float("nan")
    return acc, coverage


def evaluate_homographs(model, homographs: dict[str, list[int]], char2id, max_len, device) -> HomographEvalResult:
    if not homographs:
        return HomographEvalResult(n=0, top1=float("nan"), topk=float("nan"))
    plains = list(homographs.keys())
    preds = predict_batch(model, plains, char2id, max_len, device)
    top1_hit = topk_hit = 0
    for plain, (pred, _conf, probs) in zip(plains, preds):
        valid = homographs[plain]
        top1_hit += pred in valid
        order = torch.argsort(probs, descending=True).tolist()
        topk = set(order[:len(valid)])
        topk_hit += set(valid).issubset(topk)
    n = len(plains)
    return HomographEvalResult(n=n, top1=top1_hit / n, topk=topk_hit / n)


def print_report(corpus, model, char2id, max_len, device, confidence_threshold):
    print("\n=== Метрыкі ===")
    train_sample = random.sample(corpus.train, min(20000, len(corpus.train)))
    r_train = evaluate(model, train_sample, char2id, max_len, device)
    r_val = evaluate(model, corpus.val, char2id, max_len, device)
    r_test = evaluate(model, corpus.test, char2id, max_len, device)
    r_hom = evaluate_homographs(model, corpus.homographs, char2id, max_len, device)

    def fmt(r: EvalResult, label: str):
        print(f"{label:38s} n={r.n:>7d}  acc={r.acc:.4f}  "
              f"acc_нетрывіяльныя={r.acc_nontrivial:.4f} (n={r.n_nontrivial})")

    fmt(r_train, "Train (памяткавая sanity-мяжа)")
    fmt(r_val, "Val (lemma-disjoint)")
    fmt(r_test, "Test (lemma-disjoint)")
    print(f"{'Амографы (без кантэксту)':38s} n={r_hom.n:>7d}  top1={r_hom.top1:.4f}  topk={r_hom.topk:.4f}")

    acc_thr, cov = confidence_at_threshold(r_test.confidences, confidence_threshold)
    print(f"{'Test @ confidence>=' + str(confidence_threshold):38s} acc={acc_thr:.4f}  coverage={cov:.4f}")
    print(f"Прапушчана сегментаў: {corpus.skipped_multi_stress} (>1 націску), "
          f"{corpus.skipped_no_stress_with_vowels} (галосныя без націску)")


def main():
    args = parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    print(f"Чытаем {args.stress_list} ...")
    t0 = time.time()
    corpus = build_corpus(
        args.stress_list, val_ratio=args.val_ratio, test_ratio=args.test_ratio,
        seed=args.seed, cache_path=args.cache, rebuild_cache=args.rebuild_cache,
        max_lines=args.max_lines,
    )
    print(f"train={len(corpus.train)} val={len(corpus.val)} test={len(corpus.test)} "
          f"амографаў={len(corpus.homographs)} vocab={len(corpus.char2id)} "
          f"({time.time() - t0:.1f}s)")

    device = args.device
    print(f"Навучанне на {device} ...")
    vocab_size = len(corpus.char2id) + 2  # +PAD +UNK

    model = StressML_model(vocab_size, d_model=args.d_model, n_layers=args.n_layers,
                           n_heads=args.n_heads, dropout=args.dropout, max_len=args.max_len).to(device)
    ema_model = copy.deepcopy(model).to(device)
    for p in ema_model.parameters():
        p.requires_grad_(False)

    train_ds = StressDataset(corpus.train, corpus.char2id, max_len=args.max_len,
                              augment=True, aug_prob=args.aug_prob, unk_dropout=args.unk_dropout, seed=args.seed)
    collate = make_collate_fn(args.max_len)
    sampler = WeightedRandomSampler(
        weights=[ex.weight for ex in corpus.train], num_samples=len(corpus.train), replacement=True)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler,
                               collate_fn=collate, num_workers=args.num_workers, drop_last=True)

    total_steps = args.epochs * max(1, len(train_loader))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = build_scheduler(optimizer, total_steps, int(total_steps * args.warmup_ratio))

    best_acc = -1.0
    best_state = None
    epochs_without_improve = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        t_epoch = time.time()
        running_loss = 0.0
        n_batches = 0
        for ids, pad_mask, vowel_mask, targets, weights in train_loader:
            ids, pad_mask = ids.to(device), pad_mask.to(device)
            vowel_mask, targets, weights = vowel_mask.to(device), targets.to(device), weights.to(device)

            logits = model(ids, pad_mask, vowel_mask)
            per_sample = masked_label_smoothing_loss(logits, targets, vowel_mask, args.label_smoothing)
            loss = (per_sample * weights).sum() / weights.sum()

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            update_ema(ema_model, model, args.ema_decay)

            running_loss += loss.item()
            n_batches += 1

        r_val = evaluate(ema_model, corpus.val, corpus.char2id, args.max_len, device)
        print(f"[epoch {epoch:3d}] loss={running_loss / max(1, n_batches):.4f}  "
              f"val_acc={r_val.acc:.4f}  val_acc_нетрывіяльныя={r_val.acc_nontrivial:.4f}  "
              f"({time.time() - t_epoch:.1f}s)")

        score = float(r_val.acc_nontrivial) if r_val.n_nontrivial else float(r_val.acc)
        if score > best_acc:
            best_acc = score
            best_state = copy.deepcopy(ema_model.state_dict())
            epochs_without_improve = 0
        else:
            epochs_without_improve += 1
            if epochs_without_improve >= args.patience:
                print(f"Early stopping: няма паляпшэння {args.patience} эпох запар.")
                break

    if best_state is not None:
        ema_model.load_state_dict(best_state)

    print_report(corpus, ema_model, corpus.char2id, args.max_len, device, args.confidence_threshold)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output_dir / "stress_ml.safetensors"
    config_path = output_dir / "stress_ml_config.json"

    state_dict = {k: v.detach().cpu().contiguous() for k, v in ema_model.state_dict().items()}
    save_file(state_dict, str(weights_path))

    config = {
        "d_model": args.d_model,
        "n_layers": args.n_layers,
        "n_heads": args.n_heads,
        "max_len": args.max_len,
        "char2id": corpus.char2id,
        "vocab_size": vocab_size,
    }
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\nЗахавана: {weights_path}\nЗахавана: {config_path}")


if __name__ == "__main__":
    main()

