"""
Агульная архітэктура мадэлі пастаноўкі націску StressML.

Гэты модуль выкарыстоўваецца і пры навучанні (tools/stress_ml/train.py, праз
`belvoice.synth.stress.StressML_model`), і пры інферэнсе (StressML.py), каб
пазбегнуць дубліравання архітэктуры ў двух месцах.

Ідэя: char-level Transformer-энкодэр з выраўноўваннем па канцы слова
(left-padding, каб апошні сімвал слова заўсёды стаяў на адной і той жа
пазіцыі) і pointer-softmax толькі па пазіцыях галосных літар. Гл.
tools/stress_ml/README.md для дэталяў.
"""
import torch
import torch.nn as nn

PAD_ID = 0
UNK_ID = 1
# з гэтага id пачынаюцца "сапраўдныя" сімвалы ў char2id
FIRST_CHAR_ID = 2


class StressML_model(nn.Module):
    """
    :param vocab_size: колькасць сімвалаў у слоўніку (уключна з PAD і UNK)
    :param d_model: памернасць схаваных станаў
    :param n_layers: колькасць слаёў Transformer-энкодэра
    :param n_heads: колькасць attention-галоў
    :param dropout: dropout ва ўсіх слаях
    :param max_len: максімальная даўжыня (у сімвалах) слова/сегмента пасля выраўноўвання
    """

    def __init__(self, vocab_size: int, d_model: int = 256, n_layers: int = 6,
                 n_heads: int = 8, dropout: float = 0.15, max_len: int = 48):
        super().__init__()
        self.max_len = max_len
        self.emb = nn.Embedding(vocab_size, d_model, padding_idx=PAD_ID)
        # выраўноўванне па канцы слова: pos_rev - асноўная пазіцыйная сістэма
        # (не залежыць ад даўжыні слова ў пакеце, бо left-padding), pos_fwd - дапаможная
        self.pos_fwd = nn.Embedding(max_len, d_model)
        self.pos_rev = nn.Embedding(max_len, d_model)
        self.drop = nn.Dropout(dropout)
        layer = nn.TransformerEncoderLayer(
            d_model, n_heads, d_model * 4, dropout=dropout,
            batch_first=True, norm_first=True, activation="gelu")
        # enable_nested_tensor=False: пазбягаем UserWarning ад PyTorch, бо
        # nested-tensor оптымізацыя ўсё роўна недаступная пры norm_first=True
        self.encoder = nn.TransformerEncoder(layer, n_layers, enable_nested_tensor=False)
        self.pointer = nn.Linear(d_model, 1)

    def forward(self, ids: torch.Tensor, pad_mask: torch.Tensor, vowel_mask: torch.Tensor) -> torch.Tensor:
        """
        :param ids: [B, L] id-сімвалаў, left-padded (PAD_ID злева) так, каб апошні
                    сапраўдны сімвал заўсёды стаяў на пазіцыі L-1 (выраўноўванне па канцы слова)
        :param pad_mask: [B, L] bool, True на пазіцыях padding-у
        :param vowel_mask: [B, L] bool, True на пазіцыях галосных (сярод не-padding сімвалаў)
        :return: logits [B, L], -inf на не-галосных/padding пазіцыях (softmax толькі па галосных)
        """
        B, L = ids.shape
        device = ids.device
        ar = torch.arange(L, device=device)
        lengths = (~pad_mask).sum(dim=1, keepdim=True)  # [B, 1] - рэальная даўжыня слова
        start = (L - lengths).clamp(min=0)  # [B, 1] - індэкс першага сапраўднага сімвала

        fwd = (ar.unsqueeze(0) - start).clamp(min=0, max=self.max_len - 1)  # [B, L], ад пачатку слова
        rev = (L - 1 - ar).clamp(min=0, max=self.max_len - 1).unsqueeze(0).expand(B, L)  # [B, L], ад канца слова

        x = self.emb(ids) + self.pos_fwd(fwd) + self.pos_rev(rev)
        x = self.drop(x)
        h = self.encoder(x, src_key_padding_mask=pad_mask)

        logits = self.pointer(h).squeeze(-1)  # [B, L]
        # Увага: НЕ выкарыстоўваць torch.finfo(dtype).min тут - гэта ламае
        # label_smoothing у F.cross_entropy (ён лічыць сярэдняе log-softmax па
        # ЎСІХ класах, і сума такіх экстрэмальных значэнняў перапаўняе float32,
        # даючы loss=inf). -1e4 дастаткова "мінус бясконцасці" для softmax, але
        # бяспечна для сумавання па max_len класах.
        logits = logits.masked_fill(~vowel_mask, -1e4)
        return logits
