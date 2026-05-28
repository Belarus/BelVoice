from belvoice.asr.split.Split_SileroVAD import SplitSileroVAD

parts = SplitSileroVAD().split("test.wav")
print(parts.to_string())
