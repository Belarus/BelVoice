from transformers import AutoProcessor, SeamlessM4Tv2Model
import torchaudio

class ASR_Facebook:
    """
    See models list on the https://huggingface.co/facebook/models?search=seamless-m4t
    """
    def __init__(self, model_name: str):
        processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
        model = SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large")

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
        audio, orig_freq =  torchaudio.load(audio_file_path)
        if orig_freq != 16_000:
#            audio =  torchaudio.functional.resample(audio, orig_freq=orig_freq, new_freq=16_000)
            raise ValueError(f"Файл {audio_file_path} мае частату {orig_freq} замест 16000")
        audio_inputs = processor(audios=audio, return_tensors="pt")
        audio_array_from_audio = model.generate(**audio_inputs, tgt_lang="bel")[0].cpu().numpy().squeeze()
        return audio_array_from_audio
