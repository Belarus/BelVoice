from split.Split_SileroVAD import Split_SileroVAD

parts = Split_SileroVAD().split("test.wav")
print(parts.to_string())
