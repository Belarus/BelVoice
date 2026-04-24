from stress.StressHomonymsStat import StressHomonymsStat

text = "ё́н адка́за́ў ?"
print("Заходны тэкст: %s" % text)

text = StressHomonymsStat().apply_stresses(text)
print("Пасля статыстычнага вырашэння націскаў: %s" % text)
