from split.Split_Pyannote import Split_Pyannote

parts = Split_Pyannote().split("test.wav")
print(parts.to_string())
