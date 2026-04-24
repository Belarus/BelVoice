from phonemization.PhonemizationBelG2P import PhonemizationBelG2P

text = "ё́н адказа́ў"

text = PhonemizationBelG2P().convert(text)
print("Пасля фанемізацыі BelG2P: %s" % text)
