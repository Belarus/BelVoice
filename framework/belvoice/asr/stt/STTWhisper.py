import torch
from faster_whisper import WhisperModel


class STTWhisper:
    """
    Абгортка мадэляў OpenAI Whisper для распазнавання маўлення (Speech-to-Text).
    Глядзі спіс мадэляў на https://huggingface.co/openai/whisper-large-v3
    """

    def __init__(self, model_name: str = "large-v3", compute_type: str = None):
        """
        :param model_name: назва мадэлі для загрузкі з HuggingFace (напрыклад, 'large-v3', 'medium', 'small', 'tiny').
        """
        if torch.cuda.is_available():
            device = "cuda"
            if compute_type is None:
                compute_type = "float16"  # FP16 на Nvidia
        else:
            device = "cpu"
            if compute_type is None:
                compute_type = "float32"  # FP32 на CPU/Mac (без квантавання)

        print(f"Loading faster-whisper with model '{model_name}' on {device} with {compute_type}...")
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcript_file(self, audio_file_path: str) -> str:
        """
        Распазнае ўвесь аўдыяфайл.
        :param audio_file_path: Шлях да аўдыяфайла.
        :return: Распазнаны тэкст для ўсяго файла.
        """
        segments, info = self.model.transcribe(
            audio_file_path,
            beam_size=5,
            language="be",
            initial_prompt="Вітаю ! Гэта распазнаны тэкст па-беларуску, у якім мусяць быць знакі прыпынку — кропкі, коскі і загалоўныя літары. Што-небудзь незразумела ?",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=True
        )
        # можна выкарыстоўваць segment.start і segment.end для таймстэмпаў, калі патрэбна

        full_text = " ".join(segment.text.strip() for segment in segments).strip()
        return full_text
