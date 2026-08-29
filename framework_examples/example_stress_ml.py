from belvoice.synth.stress.StressML import StressML

text = "Пераадказаўшы недазаўважыў"
print("Зыходны тэкст: %s" % text)

text = StressML().apply_stresses(text)
print("Пасля пазначэння націскаў нейрасеткай: %s" % text)

