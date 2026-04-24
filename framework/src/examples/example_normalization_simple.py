from normalization.NormalizationSimple import NormalizationSimple

text = "Ён адказаў ABC-123"
print("Заходны тэкст: %s" % text)

text = NormalizationSimple().normalize(text)
print("Пасля нармалізацыі праз Simple: %s" % text)
