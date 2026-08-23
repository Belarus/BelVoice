import importlib.resources
import json
import re
from .common import WORD_PATTERN

class StressNoHomographs:
    """
    Пазначае націскі ў словах, якія адназначна вызначаныя ў Граматычнай базе.
    TODO: варта перарабіць на выкарыстанне marisa-trie ці LMDB
    """

    def __init__(self):
        dir = importlib.resources.files('belvoice.synth.stress')
        with (dir.joinpath('stresses-nohomographs.json').open('r', encoding='utf-8') as json_file):
            self._stresses_nohomographs = json.load(json_file)

    def apply_stresses(self, text: str) -> str:
        # Знаходзім усе беларускія словы ў тэксце
        matches = list(re.finditer(WORD_PATTERN, text, flags=re.IGNORECASE))

        result = ""
        last_end = 0
        for match in matches:
            word = match.group()
            # Дадаём у выніковы тэкст усё, што было паміж папярэднім і бягучым словам
            result += text[last_end:match.start()]
            last_end = match.end()

            if "\u0301" in word:
                # слова з ужо пазначаным націскам
                result += word
                continue

            word_lower = word.lower()

            if word in self._stresses_nohomographs:
                result += self._stresses_nohomographs[word]
            elif word_lower in self._stresses_nohomographs:
                result += self._stresses_nohomographs[word_lower]
            else:
                result += word

        # Дадаём хвост тэксту пасля апошняга знойдзенага слова
        result += text[last_end:]

        return result
