from belvoice.asr.split import Split_Pyannote

parts = Split_Pyannote().split("test.wav")
print(parts.to_string())
parts.save_to_json("test.json")
