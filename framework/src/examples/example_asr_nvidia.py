from asr.ASR_Nvidia import ASR_Nvidia
from split.SplitData import VoiceFile

asr = ASR_Nvidia("nvidia/stt_be_conformer_ctc_large")

text = asr.transcript_file("test.opus")
print(f"Тэкст з поўнага файла: {text}")

data = VoiceFile.load_from_json("test.json")
asr.transcript_parts(data)
print("Па частках:")
print(data.to_string())
