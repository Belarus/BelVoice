from normalization.NormalizationLLM import NormalizationLLM

text = "Нарадзіўся ў г. Мінску ў 1974 г."
print("Заходны тэкст: %s" % text)
text = NormalizationLLM("gemini/gemini-flash-lite-latest").normalize(text)
print("Пасля нармалізацыі праз LLM: %s" % text)
