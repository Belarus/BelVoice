"""
Падрыхтоўка дадзеных для навучання мадэлі пастаноўкі націску з stress.list.

Фармат stress.list (гл. tools/export_grammardb/src/main/java/ExportStressML.java):
    PDG_ID:форма1;форма2;...;формаN
дзе PDG_ID - id парадыгмы/лемы ў GrammarDB, а формы змяшчаюць камбінавальны акут
U+0301 адразу пасля націскной галоснай.

Ключавыя рашэнні (гл. tools/stress_ml/README.md):
- словы з дэфісам (напр. "з-пад", "абы-хто́") разбіваюцца на незалежныя сегменты
  па дэфісе; кожны сегмент з галоснай мае роўна адзін націск - гэта пацверджана
  на ўсім карпусе (няма аднаслоўных сегментаў з дзвюма пазнакамі націску);
- разбіццё train/val/test робіцца па PDG_ID (lemma-disjoint), а не па асобных
  словаформах, інакш метрыка будзе завышанай;
- амографы (адна і тая ж форма з розным націскам у розных лемах) цалкам
  выключаюцца з навучання і трапляюць у асобны eval-slice.
"""
import hashlib
import pickle
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import Dataset

STRESS = "\u0301"
VOWELS = set("аеёіоуыэюя")
CONSONANTS = set("бвгджзйклмнпрстфхцчшўьъʼ")


def strip_stress(word: str) -> str:
    return word.replace(STRESS, "")


def parse_stress_list(path: str):
    """Yields (pdg_id: int, forms: list[str]) для кожнага радка stress.list."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            pdg_id_str, _, forms_str = line.partition(":")
            if not _:
                continue
            try:
                pdg_id = int(pdg_id_str)
            except ValueError:
                continue
            forms = [w for w in forms_str.split(";") if w]
            if forms:
                yield pdg_id, forms


def split_hyphen_segments(word: str) -> list[str]:
    return [s for s in word.split("-") if s]


def find_stress(segment: str):
    """
    :return: (plain_lower, stress_index) дзе stress_index - індэкс націскной
             галоснай у plain_lower (пасля прыбірання U+0301 і lower()), або
             (plain_lower, None) калі ў сегменце няма пазнакі націску.
             Вяртае None цалкам (недапушчальны сегмент), калі знойдзена больш за
             адну пазнаку націску ў адным сегменце (у дадзеных такіх выпадкаў няма).
    """
    if segment.count(STRESS) > 1:
        return None
    idx = segment.find(STRESS)
    if idx == -1:
        return segment.lower(), None
    plain = segment[:idx] + segment[idx + 1:]
    return plain.lower(), idx - 1


def is_nontrivial(plain_lower: str) -> bool:
    """Нетрывіяльнае слова: >=2 галосныя і без 'ё' """
    n_vowels = sum(1 for c in plain_lower if c in VOWELS)
    return n_vowels >= 2 and "ё" not in plain_lower


@dataclass
class Example:
    plain: str          # сегмент у ніжнім рэгістры, без пазнакі націску
    stress_index: int    # індэкс націскной галоснай у plain
    pdg_id: int
    weight: float = 1.0


def _split_for(pdg_id: int, val_ratio: float, test_ratio: float, seed: int) -> str:
    h = int(hashlib.md5(f"{seed}:{pdg_id}".encode("utf-8")).hexdigest(), 16)
    frac = (h % 1_000_000) / 1_000_000
    if frac < test_ratio:
        return "test"
    if frac < test_ratio + val_ratio:
        return "val"
    return "train"


class Corpus:
    """
    Вынік апрацоўкі stress.list: train/val/test прыклады (lemma-disjoint,
    без амографаў), слоўнік амографаў для асобнай ацэнкі, і char-vocab.
    """

    def __init__(self):
        self.train: list[Example] = []
        self.val: list[Example] = []
        self.test: list[Example] = []
        # plain_lower -> адсартаваны список магчымых stress_index (>=2 варыянты)
        self.homographs: dict[str, list[int]] = {}
        self.char2id: dict[str, int] = {}
        self.skipped_multi_stress = 0
        self.skipped_no_stress_with_vowels = 0

    def all_nonhomograph(self):
        return self.train + self.val + self.test


def build_corpus(stress_list_path: str, val_ratio: float = 0.05, test_ratio: float = 0.05,
                  seed: int = 42, cache_path: str | None = None, rebuild_cache: bool = False,
                  max_lines: int | None = None) -> Corpus:
    cache = Path(cache_path) if cache_path else None
    if cache and cache.exists() and not rebuild_cache:
        with cache.open("rb") as f:
            return pickle.load(f)

    corpus = Corpus()

    # 1. Збіраем усе (pdg_id, plain, stress_index) без дублікатаў у межах адной лемы.
    by_pdg: dict[int, set[tuple[str, int]]] = {}
    all_plain_to_stresses: dict[str, set[int]] = {}

    for n_lines, (pdg_id, forms) in enumerate(parse_stress_list(stress_list_path)):
        if max_lines is not None and n_lines >= max_lines:
            break
        seen = by_pdg.setdefault(pdg_id, set())
        for form in forms:
            for segment in split_hyphen_segments(form):
                parsed = find_stress(segment)
                if parsed is None:
                    corpus.skipped_multi_stress += 1
                    continue
                plain, stress_index = parsed
                if stress_index is None:
                    if any(c in VOWELS for c in plain):
                        corpus.skipped_no_stress_with_vowels += 1
                    continue  # сегмент без галосных (напр. "з") - няма чаго прадказваць
                seen.add((plain, stress_index))
                all_plain_to_stresses.setdefault(plain, set()).add(stress_index)

    # 2. Амографы: адна і тая ж форма (незалежна ад лемы) з розным націскам.
    homograph_plains = {p for p, s in all_plain_to_stresses.items() if len(s) > 1}
    corpus.homographs = {p: sorted(all_plain_to_stresses[p]) for p in homograph_plains}

    # 3. Lemma-disjoint разбіццё, амографы выключаныя цалкам.
    charset: set[str] = set()
    for pdg_id, pairs in by_pdg.items():
        split = _split_for(pdg_id, val_ratio, test_ratio, seed)
        bucket = getattr(corpus, split)
        for plain, stress_index in pairs:
            if plain in homograph_plains:
                continue
            bucket.append(Example(plain=plain, stress_index=stress_index, pdg_id=pdg_id))
            charset.update(plain)

    # 4. Вагі па лемах (толькі для train, каб вялікія парадыгмы не дамінавалі).
    counts: dict[int, int] = {}
    for ex in corpus.train:
        counts[ex.pdg_id] = counts.get(ex.pdg_id, 0) + 1
    for ex in corpus.train:
        ex.weight = 1.0 / (counts[ex.pdg_id] ** 0.5)

    # 5. char2id: 0=PAD, 1=UNK, астатнія - па алфавіце (дэтэрмінавана).
    # (belvoice павінен быць усталяваны/бачны ў PYTHONPATH - гл. tools/stress_ml/README.md)
    from belvoice.synth.stress.StressML_model import FIRST_CHAR_ID
    corpus.char2id = {ch: i + FIRST_CHAR_ID for i, ch in enumerate(sorted(charset))}

    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("wb") as f:
            pickle.dump(corpus, f)

    return corpus


def augment_root_noise(plain: str, stress_index: int, char_pool_vowels: list[str],
                        char_pool_consonants: list[str], p_noise: float = 0.3, keep_tail: int = 5,
                        rng: random.Random | None = None) -> str:
    """
    Псуе 2-4 сімвалы ў "корані" слова (не чапаючы апошнія `keep_tail` сімвалаў і
    саму націскную галосную), каб мадэль вучыла правіла флексіі, а не запамінала
    канкрэтныя карані.
    """
    rng = rng or random
    if rng.random() > p_noise or len(plain) < keep_tail + 3:
        return plain
    chars = list(plain)
    zone = [i for i in range(len(chars) - keep_tail) if i != stress_index]
    if not zone:
        return plain
    n = min(len(zone), rng.randint(2, 4))
    for i in rng.sample(zone, n):
        pool = char_pool_vowels if chars[i] in VOWELS else char_pool_consonants
        if pool:
            chars[i] = rng.choice(pool)
    return "".join(chars)


class StressDataset(Dataset):
    """
    torch.utils.data.Dataset для прыкладаў пастаноўкі націску. Аугментацыя
    (шум у корань + unk-dropout) прымяняецца "на ляту" толькі калі augment=True
    (г.зн. толькі для train-спліту).
    """

    def __init__(self, examples: list[Example], char2id: dict[str, int], max_len: int = 48,
                 augment: bool = False, aug_prob: float = 0.3, unk_dropout: float = 0.01, seed: int = 0):
        self.examples = examples
        self.char2id = char2id
        self.max_len = max_len
        self.augment = augment
        self.aug_prob = aug_prob
        self.unk_dropout = unk_dropout
        self._rng = random.Random(seed)
        self._vowel_chars = sorted(c for c in char2id if c in VOWELS)
        self._consonant_chars = sorted(c for c in char2id if c in CONSONANTS)

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx: int):
        from belvoice.synth.stress.StressML_model import UNK_ID
        ex = self.examples[idx]
        plain, stress_index = ex.plain, ex.stress_index

        if self.augment:
            plain = augment_root_noise(plain, stress_index, self._vowel_chars, self._consonant_chars,
                                        p_noise=self.aug_prob, rng=self._rng)

        ids = []
        vowel_mask = []
        for i, ch in enumerate(plain):
            if self.augment and self.unk_dropout > 0 and i != stress_index and self._rng.random() < self.unk_dropout:
                ids.append(UNK_ID)
            else:
                ids.append(self.char2id.get(ch, UNK_ID))
            vowel_mask.append(ch in VOWELS)

        return {
            "ids": ids,
            "vowel_mask": vowel_mask,
            "target": stress_index,
            "weight": ex.weight,
        }


def make_collate_fn(max_len: int = 48):
    """Left-padding: апошні сапраўдны сімвал заўсёды на пазіцыі L-1 (выраўноўванне па канцы слова)."""
    import torch

    def collate(batch):
        L = min(max(len(item["ids"]) for item in batch), max_len)
        ids_batch, vowel_batch, pad_batch, targets, weights = [], [], [], [], []
        for item in batch:
            ids = item["ids"][-L:]
            vmask = item["vowel_mask"][-L:]
            clip_offset = len(item["ids"]) - len(ids)
            pad = L - len(ids)
            ids_batch.append([0] * pad + ids)
            vowel_batch.append([False] * pad + vmask)
            pad_batch.append([True] * pad + [False] * len(ids))
            targets.append(item["target"] - clip_offset + pad)
            weights.append(item["weight"])
        return (
            torch.tensor(ids_batch, dtype=torch.long),
            torch.tensor(pad_batch, dtype=torch.bool),
            torch.tensor(vowel_batch, dtype=torch.bool),
            torch.tensor(targets, dtype=torch.long),
            torch.tensor(weights, dtype=torch.float),
        )

    return collate





