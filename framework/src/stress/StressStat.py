import json
import importlib.resources
import re


class StressStat:
    def __init__(self):
        dir = importlib.resources.files('stress')
        with (dir.joinpath('stresses-nohomographs.json').open('r', encoding='utf-8') as json_file):
            self._stresses_nohomographs = json.load(json_file)
        with (dir.joinpath('stresses-stat.json').open('r', encoding='utf-8') as json_file):
            self._stresses_stat = json.load(json_file)

    def apply_stresses(self, text: str) -> str:
        word_pattern = r'([ёйцукенгшўзхфывапролджэячсмітьбю\u02BC\u0301]+)'

        parts = re.split(word_pattern, text, flags=re.IGNORECASE)
        result_parts = []
        for i, part in enumerate(parts):
            if not re.fullmatch(word_pattern, part, flags=re.IGNORECASE) or "\u0301" in part:
                # гэта не слова, альбо слова з пазначаным націскам
                continue

            part_unstressed = part.replace("\u0301", "")
            part_lower = part_unstressed.lower()

            if part_unstressed in self._stresses_nohomographs:
                parts[i] = self._stresses_nohomographs[part_unstressed]
            elif part_unstressed in self._stresses_stat:
                parts[i] = self._stresses_stat[part_unstressed]
            elif part_lower in self._stresses_nohomographs:
                parts[i] = self._stresses_nohomographs[part_lower]
            elif part_lower in self._stresses_stat:
                parts[i] = self._stresses_stat[part_lower]

        return "".join(result_parts)

    def process_word(self, word: str) -> str:
        return self._stresses_stat.get(word, self._stresses_stat.get(word.lower(), None))
