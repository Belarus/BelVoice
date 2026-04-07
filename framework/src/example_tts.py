from normalization.NormalizationLLM import NormalizationLLM
from normalization.NormalizationSimple import NormalizationSimple
from stress.StressMarkingGrammarDB import StressMarkingGrammarDB
from stress.StressHomonymsStat import StressHomonymsStat
from phonemization.PhonemizationBelG2P import PhonemizationBelG2P
from tts.TTSOmniVoice import TTSOmniVoice
from tts.TTSCoquiTTS import TTSCoquiTTS

print("====================================")

text = "Ён адказаў ABC-123"
print("Заходны тэкст: %s" % text)

text = NormalizationSimple().normalize(text)
print("Пасля нармалізацыі праз Simple: %s" % text)

text = StressMarkingGrammarDB().apply_stresses(text)
print("Пасля пазначэння націскаў: %s" % text)

text = StressHomonymsStat().apply_stresses(text)
print("Пасля статыстычнага вырашэння націскаў: %s" % text)

TTSOmniVoice().tts(text, "o1-omnivoice.wav")
print("Вынік захаваны ў o1-omnivoice.wav")

text = PhonemizationBelG2P().convert(text)
print("Пасля фанемізацыі BelG2P: %s" % text)

TTSCoquiTTS().tts(text, "o1-coqui.wav")
print("Вынік захаваны ў o1-coqui.wav")


print("====================================")

#text = "Нарадзіўся ў г. Мінску ў 1974 г."
#print("Заходны тэкст: %s" % text)
#text = NormalizationLLM("gemini/gemini-flash-lite-latest").normalize(text)
#print("Пасля нармалізацыі праз LLM: %s" % text)
