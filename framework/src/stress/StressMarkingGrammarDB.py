import json
import importlib.resources
import re


class StressMarkingGrammarDB:
    def __init__(self):
        resource_path = importlib.resources.files('stress').joinpath('stresses.json')

        with resource_path.open('r', encoding='utf-8') as json_file:
            self._stresses = json.load(json_file)

    def apply_stresses(self, text: str) -> str:
        parts = re.split('([ёйцукенгшўзхфывапролджэячсмітьбю\u02BC\u0301]+)', text, flags=re.IGNORECASE)
        result_parts = []
        for part in parts:
            if part in self._stresses:
                result_parts.append(self._stresses[part])
            elif part.lower() in self._stresses:
                result_parts.append(self._stresses[part.lower()])
            else:
                result_parts.append(part)
        return "".join(result_parts)
