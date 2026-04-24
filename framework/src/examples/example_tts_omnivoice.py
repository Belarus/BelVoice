from tts.TTSOmniVoice import TTSOmniVoice

text = "ё́н адказа́ў ?"

TTSOmniVoice().tts(text, "o1-omnivoice.wav")
print("Вынік захаваны ў o1-omnivoice.wav")
