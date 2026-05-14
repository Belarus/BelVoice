from asr.ASR_Gemini import ASR_Gemini
from split.SplitData import VoiceFile

asr = ASR_Gemini("gemini/gemini-3-flash-preview")

text = asr.transcript_file("test.flac")
print(f"Тэкст з поўнага файла: {text}")

data = VoiceFile.load_from_json("test.json")
asr.transcript_parts(data)
print("Па частках:")
print(data.to_string())

asr = ASR_Gemini("gemini/gemini-3-flash-preview", prompt="""
You are a transcription generation model specialized in Belarusian language.
Your task:
- Listen to the input audio and produce transcript in Belarusian language ONLY.
Output format:
- Return ONLY valid JSON (no markdown, no backticks).
- The JSON must be a single array of objects like:
[
  {
    "start": "00:00:00.000",
    "end":   "00:00:04.340",
    "text":  "Поўны сэнсавы сказ па-беларуску."
  },
  ...
]
Field rules:
- "start" and "end" MUST be strings in SRT time format: "HH:MM:SS.mmm".
- Times must be strictly non-decreasing along the array; segments should not overlap.
- Each "text" MUST represent a complete Belarusian sentence or a clear clause with natural punctuation.
- Do NOT artificially split sentences into 1–3 word fragments; keep them as full sentences whenever possible.
Global constraints:
- Do NOT include any other top-level keys besides the JSON array.
- Do NOT wrap the JSON in ```json``` or ``` blocks.
- Do NOT add comments, explanations, or additional text. Return raw JSON only.
""")

text = asr.transcript_file("test.flac", response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "subtitles_list",
        "schema": {
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
    }
})
print(f"JSON з поўнага файла: {text}")
