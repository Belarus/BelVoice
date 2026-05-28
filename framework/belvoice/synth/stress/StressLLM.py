import importlib.resources
import json
import litellm
import re
from litellm import completion

litellm.suppress_debug_info = True


class StressLLM:
    """
    See models list on the https://models.litellm.ai/
    Usually, you need to set LLM's token into some env variable.
    """

    PROMPT = """
    Ты - прафесійны беларускі лінгвіст. Адкажы на пытанне - які з двух варыянтаў адпавядае кантэксту. Не пішы падрабязны адказ, напішы толькі літару варыянта: {VARIANTS}.
    {GRAMMAR}

    Прааналізуй граматыку слова "{WORD}", выдзеленае квадратнымі дужкамі ў тэксце:
    """

    def __init__(self, model_name: str):
        dir = importlib.resources.files('stress')
        with (dir.joinpath('stresses-nohomographs.json').open('r', encoding='utf-8') as json_file):
            self._stresses_nohomographs = json.load(json_file)
        with (dir.joinpath('stresses-grammar.json').open('r', encoding='utf-8') as json_file):
            self._stresses_grammar = json.load(json_file)
        self._model_name = model_name

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
            elif part_lower in self._stresses_nohomographs:
                parts[i] = self._stresses_nohomographs[part_lower]
            elif part_unstressed in self._stresses_grammar or part_lower in self._stresses_grammar:
                # 1. Часова замяняем бягучае слова, дадаючы маркеры для LLM
                parts[i] = f"[{part}]"
                # 2. Збіраем поўны тэкст як кантэкст (з усімі папярэднімі зменамі + бягучы маркер)
                context_text = "".join(parts)
                # 3. Атрымліваем адказ ад LLM
                # (вам таксама трэба будзе абнавіць `request_llm` каб ён прымаў context_text замест проста слова)
                new_word = self.request_llm(context_text)[0]
                # 4. Захоўваем канчатковы варыянт у масіў
                parts[i] = new_word

        return "".join(result_parts)

    def request_llm(self, word: str, text: str) -> (str, obj):
        """
        Запыт да LLM для вызначэння націскаў у слове.
        :param word: слова, у якім трэба вызначыць націск
        :param text: тэкст для апрацоўкі, дзе слова пазначана квадратнымі дужкамі
        :return: слова з націскам (\u0301)
        """

        grammar = self._stresses_grammar.get(word)
        if not grammar:
            grammar = self._stresses_grammar.get(word.lower())
        if not grammar:
            return None, None

        variants = '"A", "B" ці "C"' if len(grammar["stressByVariant"]) == 3 else '"A" ці "B"'

        messages = [
            {"role": "system",
             "content": self.PROMPT
             .replace("{GRAMMAR}", grammar["promptText"])
             .replace("{WORD}", word)
             .replace("{VARIANTS}", variants)},
            {"role": "user", "content": text}
        ]

        response = completion(
            model=self._model_name,
            messages=messages,
            temperature=0.0
            # thinking дадаецца такім чынам для gemma праз openrouter model="openai/google/gemma-4-26b-a4b-it":
            # extra_body={
            #     "chat_template_kwargs": {
            #         "enable_thinking": True
            #     }
            # }
            # thinking задаецца такім чынам для gemma праз model="gemini/gemma-4-26b-a4b-it":
            # thinking_level="high",
        )
        result_variant = response.choices[0].message.content
        return (grammar["stressByVariant"][result_variant], response)

# Праблемныя - трэба тлумачальны: зараз, лісце, нарадзіцца, гадзіна, хапала, вады
