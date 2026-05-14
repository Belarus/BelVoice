from stress.StressLLM import StressLLM

text = "Ён адказаў ?"
text = StressLLM("openrouter/google/gemini-3.1-flash-lite").apply_stresses(text)
print("Пасля пазначэння націскаў: %s" % text)
