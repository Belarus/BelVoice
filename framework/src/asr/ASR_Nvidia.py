import nemo.collections.asr as nemo_asr

class ASR_Nvidia:
    """
    See models list on the https://huggingface.co/nvidia/models?search=stt_be
    """
    def __init__(self, model_name: str):
        MODEL_LOADERS = {
            "nvidia/stt_be_fastconformer_hybrid_large_pc": lambda: nemo_asr.models.EncDecHybridRNNTCTCBPEModel.from_pretrained(model_name="nvidia/stt_be_fastconformer_hybrid_large_pc"),
            "nvidia/stt_be_conformer_transducer_large": lambda: nemo_asr.models.EncDecRNNTBPEModel.from_pretrained("nvidia/stt_be_conformer_transducer_large"),
            "nvidia/stt_be_conformer_ctc_large": lambda: nemo_asr.models.EncDecCTCModelBPE.from_pretrained("nvidia/stt_be_conformer_ctc_large")
        }

        if model_name in MODEL_LOADERS:
            print(f"Загружаем мадэль: {model_name}")
            self._asr_model = MODEL_LOADERS[model_name]()
        else:
            available_models = ", ".join(MODEL_LOADERS.keys())
            raise ValueError(
                f"Памылка: мадэль '{model_name}' невядомая. "
                f"Даступныя варыянты: [{available_models}]"
            )

    def transcript(self, audio_file_path: str) -> str:
        if not audio_file_path.endswith(".wav"):
            raise Exception(f"{audio_file_path} is not a wav file")
        output = self._asr_model.transcribe([audio_file_path])
        return output[0].text
