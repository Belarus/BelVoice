import importlib.resources
import json
import re
from collections.abc import Callable
from pathlib import Path

import torch
from safetensors.torch import load_file

from .common import WORD_PATTERN
from .StressML_model import StressML_model, UNK_ID

VOWELS = set("аеёіоуыэюя")
STRESS = "\u0301"


class StressML:
    """
    Пазначае націск у слове нейрасеткай (char-Transformer, pointer-softmax па
    галосных, выраўноўванне па канцы слова). Прызначана перадусім для слоў,
    якіх няма ў слоўніку (гл. StressNoHomographs/StressStat) - гл.
    tools/stress_ml/README.md для апісання ідэі, дадзеных і навучання.

    Патрабуе асобна ўсталяваныя `torch` і `safetensors`
    (гл. tools/stress_ml/requirements.txt) - яны наўмысна не ў залежнасцях BelVoice.
    """

    def __init__(self,
                 weights_file=None,
                 config_file=None,
                 callback: Callable[[float], None] | None = None):
        res_dir = importlib.resources.files('belvoice.synth.stress')
        weights_file = Path(weights_file) if weights_file else res_dir.joinpath('stress_ml.safetensors')
        config_file = Path(config_file) if config_file else res_dir.joinpath('stress_ml_config.json')

        with config_file.open('r', encoding='utf-8') as f:
            config = json.load(f)

        self._char2id: dict = config['char2id']
        self._max_len: int = config['max_len']

        self._model = StressML_model(
            vocab_size=config['vocab_size'],
            d_model=config['d_model'],
            n_layers=config['n_layers'],
            n_heads=config['n_heads'],
            dropout=0.0,
            max_len=self._max_len,
        )
        state_dict = load_file(str(weights_file))
        self._model.load_state_dict(state_dict)
        self._model.eval()
        self._callback = callback

    @torch.no_grad()
    def _predict_segment(self, segment: str):
        """
        :return: (індэкс націскной галоснай у segment, упэўненасць) або
                 (None, None), калі ў сегменце няма галосных наогул.
        """
        lower = segment.lower()
        vowel_idx = [i for i, ch in enumerate(lower) if ch in VOWELS]
        if not vowel_idx:
            return None, None
        if len(vowel_idx) == 1:
            return vowel_idx[0], 1.0

        clipped = lower[-self._max_len:]
        offset = len(lower) - len(clipped)  # колькі сімвалаў абрэзана з пачатку (на выпадак вельмі доўгіх слоў)
        ids = [self._char2id.get(c, UNK_ID) for c in clipped]
        pad = self._max_len - len(ids)
        ids_padded = [0] * pad + ids
        vowel_mask = [False] * pad + [c in VOWELS for c in clipped]

        ids_t = torch.tensor([ids_padded], dtype=torch.long)
        pad_mask_t = torch.tensor([[i < pad for i in range(self._max_len)]], dtype=torch.bool)
        vowel_mask_t = torch.tensor([vowel_mask], dtype=torch.bool)

        logits = self._model(ids_t, pad_mask_t, vowel_mask_t)[0]
        probs = torch.softmax(logits, dim=-1)
        pred = int(torch.argmax(probs).item())
        confidence = float(probs[pred].item())

        idx_in_lower = (pred - pad) + offset
        return idx_in_lower, confidence

    def _stress_segment(self, segment: str):
        idx, confidence = self._predict_segment(segment)
        if idx is None:
            return segment, None
        return segment[:idx + 1] + STRESS + segment[idx + 1:], confidence

    def process_word(self, word: str) -> tuple[str, float]:
        """
        Пазначае націск у адным слове. Дэфісныя словы (напр. "з-пад", "абы-хто")
        апрацоўваюцца па частках незалежна.
        :return: (слова з націскам, найменшая ўпэўненасць сярод дэфісных частак)
        """
        parts = word.split('-')
        out_parts = []
        confidences = []
        for part in parts:
            stressed, confidence = self._stress_segment(part)
            out_parts.append(stressed)
            if confidence is not None:
                confidences.append(confidence)
        return '-'.join(out_parts), (min(confidences) if confidences else 1.0)

    def apply_stresses(self, text: str) -> str:
        # Знаходзім усе беларускія словы ў тэксце
        matches = list(re.finditer(WORD_PATTERN, text, flags=re.IGNORECASE))
        if not matches:
            if self._callback:
                self._callback(100.0)
            return text

        total_words = len(matches)
        result = ""
        last_end = 0
        for i, match in enumerate(matches):
            word = match.group()
            # Дадаём у выніковы тэкст усё, што было паміж папярэднім і бягучым словам
            result += text[last_end:match.start()]
            last_end = match.end()

            if STRESS in word:
                # слова з ужо пазначаным націскам
                result += word
                continue

            stressed, _confidence = self.process_word(word)
            result += stressed

            if self._callback:
                self._callback((i + 1) / total_words * 100.0)

        # Дадаём хвост тэксту пасля апошняга знойдзенага слова
        result += text[last_end:]

        return result
