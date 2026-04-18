from typing import List
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline


class ASR_Facebook:
    """
    Глядзі спіс мадэляў на https://github.com/facebookresearch/omnilingual-asr
    Найлепшыя вынікі дае omniASR_LLM_Unlimited_*_v2
    """

    def __init__(self, model_card: str = "omniASR_LLM_Unlimited_1B_v2", lang: str = "bel_Cyrl", batch_size: int = 1):
        self._pipeline = ASRInferencePipeline(model_card)
        self._languages = [lang]
        self._batch_size = batch_size

    def transcript(self, audio_file_path: str) -> List[str]:
        transcriptions = self._pipeline.transcribe([audio_file_path], lang=self._languages, batch_size=self._batch_size)
        return transcriptions
