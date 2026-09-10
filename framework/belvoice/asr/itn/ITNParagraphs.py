import json
import re
import time
from pathlib import Path
from typing import Optional, Union

import litellm

litellm.suppress_debug_info = True

from litellm import completion


class ITNParagraphs:
    """
    Зваротная нармалізацыя тэксту (ITN): разбіўка на лагічныя абзацы праз LLM (litellm).
    """

    PROMPT = """The following text is pre-split into numbered sentences with {{{id}}} tags. Decide where new paragraphs should logically begin.
Return ONLY a JSON list of sentence IDs that should START a new paragraph (do not include sentence 1).

Example output: [4, 9, 15]"""

    def __init__(self, model_name: str, batch_size: int = 50, prompt: Optional[str] = None):
        self._model_name = model_name
        self._batch_size = batch_size
        self._prompt = prompt or self.PROMPT

    def _split_sentences(self, text: str) -> list[str]:
        """
        Ігнаруе папярэдняе фарматаванне і разбівае тэкст на сказы па знаках прыпынку.
        """
        text = " ".join(text.split())
        if not text:
            return []
        raw_sentences = re.split(r'(?<=[.!?…]["\'”»])\s+|(?<=[.!?…])\s+', text)
        return [s.strip() for s in raw_sentences if s.strip()]

    def _parse_response(self, content: str, valid_range: tuple[int, int], batch_len: int) -> list[int]:
        if not content:
            raise ValueError("Пусты адказ ад LLM.")

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        start_bracket = cleaned.find("[")
        end_bracket = cleaned.rfind("]")
        if start_bracket == -1 or end_bracket == -1 or end_bracket < start_bracket:
            raise ValueError(f"Не знойдзены JSON-спіс у адказе LLM: {content}")

        json_str = cleaned[start_bracket : end_bracket + 1]
        data = json.loads(json_str)

        if not isinstance(data, list):
            raise ValueError(f"Чакаўся JSON-спіс, але атрымана: {type(data)}")

        raw_ids: list[int] = []
        for item in data:
            try:
                raw_ids.append(int(item))
            except (ValueError, TypeError):
                raise ValueError(f"Недапушчальны ID сказа ў спісе: {item}")

        min_id, max_id = valid_range
        # Калі мадэль памылкова выкарыстала лакальную нумарацыю (1..batch_len) замест глабальнай
        if min_id > 1 and raw_ids and all(x < min_id for x in raw_ids) and all(1 <= x <= batch_len for x in raw_ids):
            raw_ids = [min_id + x - 1 for x in raw_ids]

        result: list[int] = []
        for val in raw_ids:
            if val == 1:
                continue
            if not (min_id <= val <= max_id):
                raise ValueError(f"ID сказа {val} знаходзіцца па-за дыяпазонам батча [{min_id}, {max_id}]")
            result.append(val)

        return result

    def _query_batch(self, formatted_batch: str, valid_range: tuple[int, int], batch_len: int) -> list[int]:
        messages = [
            {"role": "system", "content": self._prompt},
            {"role": "user", "content": formatted_batch}
        ]

        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = completion(
                    model=self._model_name,
                    messages=messages,
                    temperature=0.0
                )
                content = response.choices[0].message.content or ""
                return self._parse_response(content, valid_range, batch_len)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** (attempt - 1))

        min_id, max_id = valid_range
        raise RuntimeError(
            f"Не атрымалася апрацаваць батч сказаў {{{min_id}}}..{{{max_id}}} пасля {max_retries} спроб: {last_error}"
        ) from last_error

    def restore_paragraphs_from_sentences(self, sentences: list[str]) -> str:
        """
        Аднаўляе абзацы па гатовым спісе сказаў.
        """
        if not sentences:
            return ""
        if len(sentences) == 1:
            return sentences[0]

        paragraph_start_ids: set[int] = set()

        for i in range(0, len(sentences), self._batch_size):
            batch = sentences[i : i + self._batch_size]
            batch_start_id = i + 1
            batch_end_id = i + len(batch)

            formatted_batch = "\n".join(
                f"{{{{{{{idx}}}}}}} {sentence}"
                for idx, sentence in enumerate(batch, start=batch_start_id)
            )

            batch_ids = self._query_batch(
                formatted_batch,
                valid_range=(batch_start_id, batch_end_id),
                batch_len=len(batch)
            )
            paragraph_start_ids.update(batch_ids)

        paragraphs: list[list[str]] = []
        current_paragraph: list[str] = []

        for idx, sentence in enumerate(sentences, start=1):
            if idx in paragraph_start_ids and current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = []
            current_paragraph.append(sentence)

        if current_paragraph:
            paragraphs.append(current_paragraph)

        return "\n\n".join(" ".join(p) for p in paragraphs)

    def restore_paragraphs(self, text: str) -> str:
        """
        Разбівае сыры тэкст на сказы і збірае іх у лагічныя абзацы.
        """
        sentences = self._split_sentences(text)
        return self.restore_paragraphs_from_sentences(sentences)

    def normalize(self, text_to_normalize: str) -> str:
        """
        Аналаг метаду normalize для аднастайнасці з NormalizationLLM.
        """
        return self.restore_paragraphs(text_to_normalize)

    def process_file(self, input_file_path: Union[str, Path], output_file_path: Optional[Union[str, Path]] = None) -> str:
        """
        Чытае тэкст з файла, выконвае разбіўку на абзацы і апцыянальна захоўвае вынік у output_file_path.
        """
        input_path = Path(input_file_path)
        text = input_path.read_text(encoding="utf-8")
        result = self.restore_paragraphs(text)

        if output_file_path is not None:
            output_path = Path(output_file_path)
            output_path.write_text(result, encoding="utf-8")

        return result

