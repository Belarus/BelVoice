from stress.StressMarkingGrammarDB import StressMarkingGrammarDB

text = "Ён адказаў ?"
text = StressMarkingGrammarDB().apply_stresses(text)
print("Пасля пазначэння націскаў: %s" % text)
