import json
import os
import re
from typing import Optional, Literal

from google import genai
from google.genai import types
from google.genai.types import ThinkingConfig, ThinkingLevel

from belvoice.asr.SplitData import VoiceFile, VoicePart


class STTGemini:
    PROMPT = """
    Act as a professional transcriber. Provide a detailed, verbatim text transcript of this Belarusian audio file.
    Do not place timestamps. Do not add comments, explanations, or additional text.
    """

    PROMPT_TIMESTAMPS = """
    You are a transcription generation model specialized in Belarusian language.
    Your task:
    - Listen to the input audio and produce a verbatim text transcript.
    Output format:
    - Return ONLY valid JSON (no markdown, no backticks).
    - The JSON must be a single array of objects like:
    [
      {
        "start": "00:00.000",
        "end":   "00:04.340",
        "text":  "Поўны сэнсавы сказ па-беларуску."
      },
      ...
    ]
    Field rules:
    - "start" and "end" MUST be strings in SRT time format: "MM:SS.mmm".
    - Times must be strictly non-decreasing along the array; segments should not overlap.
    - Each "text" MUST represent a complete Belarusian sentence or a clear clause with natural punctuation.
    - Do NOT artificially split sentences into 1–3 word fragments; keep them as full sentences whenever possible.
    Global constraints:
    - Do NOT include any other top-level keys besides the JSON array.
    - Do NOT wrap the JSON in ```json``` or ``` blocks.
    - Do NOT add comments, explanations, or additional text. Return raw JSON only.
    """

    RESPONSE_FORMAT_TIMESTAMPS_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "text": {"type": "string"}
            },
            "required": ["start", "end", "text"],
            "additionalProperties": False
        }
    }

    MIME_TYPES = {
        "wav": "audio/x-wav",  # "audio/x-wav",
        "opus": "audio/ogg",
        "mp3": "audio/mp3",
        "ogg": "audio/ogg",
        "aac": "audio/aac",
        "flac": "audio/flac"
    }

    def __init__(self, model_name: str, prompt: str = None,
                 thinking_level: Optional[Literal["none", "minimal", "low", "medium", "high"]] = "none",
                 audio_transcription_config: Optional[types.AudioTranscriptionConfig] = None) -> None:
        if os.environ.get("GEMINI_API_KEY") is None:
            raise Exception("Памылка: не ўстаноўлены GEMINI_API_KEY у якасці зменнай асяроддзя.")

        self._model_name = model_name
        self._prompt = prompt
        self._thinking_level = thinking_level
        self._client = genai.Client()
        self._audio_transcription_config = audio_transcription_config

    def transcript_file(self, audio_file_path: str, convert_to_format: str = None) -> str:
        """
        Робіць транскрыпт усяго файла без разбіўкі на сегменты.
        """
        if convert_to_format:
            temp_file = VoiceFile.extract_wav(audio_file_path, convert_to_format=convert_to_format)
        else:
            temp_file = audio_file_path
        response = self._transcript_file(temp_file, self._prompt if self._prompt else self.PROMPT, None)
        if convert_to_format:
            os.remove(temp_file)

        return response.text

    def transcript_parts(self, data: VoiceFile) -> None:
        """
        Робіць транскрыпт для кожнага сегмента, але без унутраных таймстэмпаў і пераразбіўкі сегментаў.
        """
        for segment in data.segments:
            if segment.text:
                continue
            if segment.end - segment.start >= 0.2:  # толькі часткі даўжэйшыя за 0.2 секунды
                self.transcript_part(data, segment)

    def transcript_part(self, data: VoiceFile, segment: VoicePart) -> None:
        """
        Робіць транскрыпт для аднаго сегмента.
        """
        temp_file = data.segment2wav(segment)
        try:
            response = self._transcript_file(temp_file, self._prompt if self._prompt else self.PROMPT, None)
        finally:
            os.remove(temp_file)

        segment.text = response.text

    def transcript_parts_with_timestamps(self, data: VoiceFile, segment_processed_callback=None) -> None:
        """
        Робіць транскрыпт з таймстэмпамі для кожнага сегмента, і разбівае сегменты адпаведна выніковым таймстэмпам.
        То бок калі даўжыня аднаго сегмента некалькі хвілін, транскрыпт вяртае некалькі выніковых сегментаў для гэтага аднаго,
        і яны замяняюць той адзін зыходны сегмент у выніковым файле.
        Апрацоўвае толькі тыя сегменты, дзе яшчэ няма транскрыпту.
        """
        i = 0
        while i < len(data.segments):
            segment = data.segments[i]
            if segment.text:
                i += 1
                continue
            if segment.end - segment.start < 0.2:
                i += 1
                segment.text = ""
                continue

            temp_file = data.segment2wav(segment)
            response = self._transcript_file(temp_file, self._prompt if self._prompt else self.PROMPT_TIMESTAMPS,
                                             self.RESPONSE_FORMAT_TIMESTAMPS_SCHEMA)
            os.remove(temp_file)

            transcript = response.text

            if segment_processed_callback:
                segment_processed_callback(segment)

            replace_segments: list[VoicePart] = self._convert_transcript_to_segments(segment, transcript)

            data.segments[i: i + 1] = replace_segments  # замяняем на сегменты з Gemini
            i += len(replace_segments)

    def _transcript_file(self, temp_file: str, prompt: str, schema: dict):
        audio_file = self._client.files.upload(file=temp_file)
        try:
            if self._audio_transcription_config:
                response = self._client.interactions.create(
                    model=self._model_name,
                    input=audio_file,
                    config=types.GenerateContentConfig(
                        audio_transcription_config=self._audio_transcription_config
                    )
                )
            else:
                if schema:
                    config = types.GenerateContentConfig(temperature=0,
                                                         # response_mime_type="application/json", response_schema=schema,
                                                         audio_timestamp=True)
                else:
                    config = types.GenerateContentConfig(temperature=0,
                                                         thinking_config=ThinkingConfig(
                                                             thinking_level=ThinkingLevel.MINIMAL))
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=[prompt, audio_file],
                    config=config
                )
        finally:
            self._client.files.delete(name=audio_file.name)

        return response

    def _convert_transcript_to_segments(self, source_segment: VoicePart, transcript: str) -> list[VoicePart]:
        """
        Правярае, ці з'яўляецца транскрыпт сапраўдным JSON з правільнымі таймстэмпамі і тэкстам.
        """
        result_segments: list[VoicePart] = []
        try:
            data = json.loads(transcript)
        except json.JSONDecodeError as e:
            raise Exception(f"Невалідны json: {e}:\n\n{transcript}")

        if not isinstance(data, list):
            raise Exception("Вынік - не спіс сегментаў")
        last_end = None
        for item in data:
            if not isinstance(item, dict):
                raise Exception("Адзін сегмент - не аб'ект з start/end/text")
            if "start" not in item or "end" not in item or "text" not in item:
                raise Exception("Адзін сегмент - не аб'ект з start/end/text")
            # Правяраем фармат часу
            if not re.match(r"^\d{1,2}:\d{1,2}\.\d{1,3}$", item["start"]):
                raise Exception(f"Поле start - няправільнае ў {item}")
            if not re.match(r"^\d{1,2}:\d{1,2}\.\d{1,3}$", item["end"]):
                raise Exception(f"Поле end - няправільнае ў {item}")
            if not isinstance(item["text"], str):
                raise Exception(f"Поле text - не string у {item}")

            # Канвертуем у секунды
            start_min, start_sec = item["start"].split(":")
            start_seconds = float(start_min) * 60 + float(start_sec)

            end_min, end_sec = item["end"].split(":")
            end_seconds = float(end_min) * 60 + float(end_sec)

            # Простая праверка парадку
            if start_seconds > end_seconds:
                raise Exception(f"Поле start > end у {item}")
            if last_end and start_seconds < last_end:
                raise Exception(f"Поле start < папярэдняга end у {item}")
            last_end = end_seconds

            result_segments.append(
                VoicePart(start=source_segment.start + start_seconds, end=source_segment.start + end_seconds,
                          speaker_id=source_segment.speaker_id,
                          text=item["text"]))

        if last_end and last_end > (source_segment.end - source_segment.start + 2):
            raise Exception(
                f"Поле end={last_end} сегментаў больш чымся на 2 секунды перавышае даўжыню зыходнага сегмента {source_segment.end - source_segment.start} секунд")

        return result_segments
