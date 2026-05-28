from belvoice.synth.stress import StressStat

text = "Ён адказаў ?"
print("Заходны тэкст: %s" % text)

text = StressStat().apply_stresses(text)
print("Пасля статыстычнага вырашэння націскаў: %s" % text)
