from asr.ASR_Facebook import ASR_Facebook
from split.SplitData import VoiceFile

asr = ASR_Facebook("omniASR_LLM_Unlimited_300M_v2")

text = asr.transcript_file("test.wav")
print(f"Тэкст з поўнага файла: {text}")

data = VoiceFile.load_from_json("test.json")
asr.transcript_parts(data)
print("Па частках:")
print(data.to_string())
