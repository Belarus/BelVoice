from belvoice.asr.stt.ASR_Nvidia import SttNvidia
from belvoice.asr.split import VoiceFile

asr = SttNvidia("nvidia/stt_be_conformer_ctc_large")

text = asr.transcript_file("test.opus")
print(f"Тэкст з поўнага файла: {text}")

data = VoiceFile.load_from_json("test.json")
asr.transcript_parts(data)
print("Па частках:")
print(data.to_string())
