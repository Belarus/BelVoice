import re
from .common import WORD_PATTERN

class StressUsual:
    """
    Пазначае націск у слове, калі ў ім ёсць роўна адна літара 'о' альбо 'ё'
    """

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

            positions = [i for i, ch in enumerate(word) if ch in ('о', 'О', 'ё', 'Ё')]

            if len(positions) == 1:
                pos = positions[0]
                result += word[:pos + 1] + "\u0301" + word[pos + 1:]
            else:
                result += word

        # Дадаём хвост тэксту пасля апошняга знойдзенага слова
        result += text[last_end:]

        return result

