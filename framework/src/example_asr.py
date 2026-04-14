#from asr.ASR_Gemini import ASR_Gemini
#from asr.ASR_Nvidia import ASR_Nvidia
from asr.ASR_Facebook import ASR_Facebook

print("====================================")
#ASRLLM("whisper-1").transcript("/home/alex/test.flac")
#text = ASR_Gemini("gemini/gemini-3-flash-preview").transcript("/home/alex/test.flac")
#text = ASR_Nvidia("nvidia/stt_be_fastconformer_hybrid_large_pc").transcript("/tmp/test.wav")
#text = ASR_Nvidia("nvidia/stt_be_conformer_transducer_large").transcript("framework/src/tts/tts-omnivoice/ref.wav")
#text = ASR_Nvidia("nvidia/stt_be_conformer_ctc_large").transcript("framework/src/tts/tts-omnivoice/ref.wav")
text = ASR_Facebook("facebook/seamless-m4t-v2-large").transcript("/tmp/test.wav")
print(text)
