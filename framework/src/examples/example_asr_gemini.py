from asr.ASR_Gemini import ASR_Gemini
from split.SplitData import VoiceFile

asr = ASR_Gemini("gemini/gemini-3.1-flash-lite-preview")

text = asr.transcript_file("test.flac")
print(f"Тэкст з поўнага файла: {text}")

data = VoiceFile.load_from_json("test.json")
asr.transcript_parts(data)
print("Па частках:")
print(data.to_string())
