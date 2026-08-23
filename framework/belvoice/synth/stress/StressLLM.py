import importlib.resources
import litellm
import re
from collections.abc import Callable
from litellm import completion
from .common import WORD_PATTERN, word_match_case

litellm.suppress_debug_info = True


class StressLLM:
    """
    See models list on the https://models.litellm.ai/
    Usually, you need to set LLM's token into some env variable.

    Параметры thinking перадаюцца ў залежнасці ад мадэлі і правайдэра:
    для gemini/gemma-4-31b-it і для openrouter/google/gemma-4-31b-it яны будуць розныя.
    Стандартнае значэнне thinking, калі яго не перадаваць, залежыць ад LiteLLM і правайдэраў.

    Аманімія ўласных назваў і звычайных слоў можа праходзіць па спрошчанай форме, калі слова стаіць пасярод сказу.
    Такім чынам, калі для ўсіх варыянтаў з малой літары націскі аднолькавыя - будзе вяртацца націск без выкліку LLM.
    Тое самае і з вялікай літары. Але, калі слова стаіць напачатку сказа, абавязкова будзе выклікацца LLM.
    """

    PROMPT = """
You are an expert linguist.
Analyze the context of the word '[{WORD}]' enclosed in square brackets in the Belarusian language text.
Determine which of the {VARIANTS_COUNT} dictionary variants ({VARIANTS}) correctly describes the highlighted word.

CRITICAL FORMATTING RULES:
- Output EXACTLY ONE letter: {VARIANTS}.
- No explanations, no punctuation, no extra words.

<dictionary>
{DICTIONARY}
</dictionary>
"""
    CONTEXT_WORDS_COUNT = 25  # колькі слоў захоўваць да вызначанага слова і пасля

    def __init__(self, model_name: str,
                 requests_file: str = importlib.resources.files('belvoice.synth.stress').joinpath("stresses-grammar_optimized.md"),
                 reasoning_effort: str = None,
                 extra_body: dict = None,
                 callback: Callable[[float], None] | None = None):
        with requests_file.open('r', encoding='utf-8') as md_file:
            self._stresses_prompts, self._stresses_variants = self._load_optimized(md_file)
        self._model_name = model_name
        self._reasoning_effort = reasoning_effort
        self._extra_body = extra_body if extra_body else {}
        self._callback = callback

    def _parse_variants(self, header) -> (str, dict):
        parts = header.lstrip('#').split(';')
        result = dict()
        for part in parts:
            part = part.strip()
            match = re.fullmatch(r'([A-Z]):\s*([^;\s]+)', part)
            if match is None:
                raise ValueError(f"Invalid header format: {header}")
            if match.group(1) != chr(ord('A') + len(result)):
                raise ValueError(f"Invalid header format: {header}")
            result[match.group(1)] = match.group(2)

        unstressed_lower_set = {key.replace('\u0301', '').lower() for key in result.values()}
        if len(unstressed_lower_set) != 1:
            raise ValueError(f"Invalid header format: {header}. All variants must have the same unstressed form.")

        return next(iter(unstressed_lower_set)), result

    def _load_optimized(self, md_file):
        content = md_file.read()
        result_prompts = {}
        result_variants = {}
        current_header = None
        current_lines = []

        for line in content.splitlines():
            if line.startswith('#') and not line.startswith('##'):
                if current_header is not None:
                    block_text = "\n".join(current_lines).strip()
                    result_prompts[current_header] = block_text
                current_header, current_variants = self._parse_variants(line)
                result_variants[current_header] = current_variants
                current_lines = []
            else:
                if current_header is not None:
                    current_lines.append(line)

        if current_header is not None:
            block_text = "\n".join(current_lines).strip()
            result_prompts[current_header] = block_text

        return result_prompts, result_variants

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

            if "\u0301" in word:
                # слова з ужо пазначаным націскам
                result += word
            else:
                word_lower = word.lower()

                if word_lower not in self._stresses_variants:
                    result += word
                else:
                    variants = self._stresses_variants[word_lower]
                    dictionary = self._stresses_prompts.get(word_lower)

                    if len(variants) == 1:
                        # Адзіны варыянт - націск вядомы адназначна, LLM не патрэбны
                        result += word_match_case(word, variants['A'])
                    elif not self._is_sentence_start(text, match.start()) and (fixed := self._fixed_stress_word(word, variants)) is not None:
                        result += fixed
                    else:
                        # 1. Збіраем кантэкст: 25 слоў да і 25 слоў пасля, бягучае слова адзначаем дужкамі
                        if i > self.CONTEXT_WORDS_COUNT:
                            context_before = "... " + text[matches[i - self.CONTEXT_WORDS_COUNT].start():match.start()]
                        else:
                            context_before = text[:match.start()]
                        if i < len(matches) - self.CONTEXT_WORDS_COUNT:
                            context_after = text[match.end():matches[i + self.CONTEXT_WORDS_COUNT].end()] + " ..."
                        else:
                            context_after = text[match.end():]
                        context_text = f"{context_before}[{word}]{context_after}"
                        # 2. Атрымліваем адказ ад LLM
                        new_word = self._request_llm(word, context_text, variants, dictionary)
                        # 3. Захоўваем канчатковы варыянт (калі LLM не змагла адказаць - пакідаем зыходнае слова)
                        result += word_match_case(word, new_word) if new_word else word

            if self._callback:
                self._callback((i + 1) / total_words * 100.0)

        # Дадаём хвост тэксту пасля апошняга знойдзенага слова
        result += text[last_end:]

        return result

    def _is_sentence_start(self, text: str, start_index: int) -> bool:
        """
        Правярае, ці стаіць слова, якое пачынаецца з `start_index`, на пачатку сказа/радка.
        Глядзім сімвалы перад словам: калі сустракаецца літара, апостраф ці коска - гэта не
        пачатак сказа. Калі сустракаецца прагал - глядзім папярэдні сімвал. Усе астатнія
        сімвалы (у тым ліку адсутнасць тэксту да гэтага месца) лічацца пачаткам сказа.
        """
        idx = start_index - 1
        while idx >= 0 and text[idx].isspace():
            idx -= 1
        if idx < 0:
            return True
        if text[idx].isalpha() or text[idx] in "'\u02BC\u2019,":
            return False
        return True

    def _has_mixed_case_variants(self, variants: dict) -> bool:
        """
        Правярае, ці ёсць у variants адначасова словы, якія пачынаюцца
        з вялікай і з малой літары (напрыклад, уласная назва і агульны
        назоўнік).
        """
        has_upper = any(value[0].isupper() for value in variants.values())
        has_lower = any(value[0].islower() for value in variants.values())
        return has_upper and has_lower

    def _fixed_stress_word(self, word: str, variants: dict) -> str | None:
        """
        Калі ў variants ёсць словы і з малой, і з вялікай літары, разглядаюцца
        толькі тыя варыянты, чый рэгістр першай літары супадае з рэгістрам
        зыходнага слова. Калі ўсе такія варыянты (з улікам націску) супадаюць
        паміж сабой, вяртаецца першы з іх без звароту да LLM. Інакш (у тым
        ліку калі рэгістр у variants аднолькавы для ўсіх слоў) вяртае None.
        """
        if not self._has_mixed_case_variants(variants):
            return None
        capitalized = word[0].isupper()
        candidates = [value for value in variants.values() if value[0].isupper() == capitalized]
        if not candidates or any(value != candidates[0] for value in candidates):
            return None
        return candidates[0]

    def _request_llm(self, word: str, text: str, variants: dict, dictionary: str) -> str:
        """
        Запыт да LLM для вызначэння націскаў у слове.
        :param word: слова, у якім трэба вызначыць націск
        :param text: тэкст для апрацоўкі, дзе слова пазначана квадратнымі дужкамі
        :param variants: слоўнікавыя варыянты слова (не менш за 2)
        :param dictionary: прампт-блок з апісаннем варыянтаў
        :return: слова з націскам (\u0301)
        """

        if len(variants) == 2:
            variants_str = 'A or B'
        elif len(variants) == 3:
            variants_str = 'A, B or C'
        elif len(variants) == 4:
            variants_str = 'A, B, C or D'
        else:
            raise ValueError(f"Invalid number of variants for word '{word}': {len(variants)}. Expected 2, 3 or 4.")

        messages = [
            {"role": "system",
             "content": self.PROMPT
             .replace("{WORD}", word)
             .replace("{DICTIONARY}", dictionary)
             .replace("{VARIANTS}", variants_str)
             .replace("{VARIANTS_COUNT}", str(len(variants)))},
            {"role": "user", "content": text}
        ]

        response = completion(
            model=self._model_name,
            timeout=60,
            messages=messages,
            temperature=0.0,
            reasoning_effort=self._reasoning_effort,
            allowed_openai_params=['reasoning_effort'],
            extra_body=self._extra_body
        )
        if response.choices[0].message.content is None:
            return None
        result_variant = response.choices[0].message.content.strip()
        result = variants[result_variant] if result_variant in variants else None
        return result
