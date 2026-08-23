import os
from typing import List

import nemo.collections.asr as nemo_asr
import torch

from belvoice.asr.SplitData import VoiceFile, VoicePart


class STTNvidia:
    """
    Абгортка мадэлі Nvidia NeMo ASR для распазнавання маўлення (Speech-to-Text).
    Глядзі спіс мадэляў на https://huggingface.co/nvidia/models?search=stt_be
    """

    def __init__(self, model_name: str, att_context_size: List[int] = None, batch_size=4):
        """
        :param model_name: назва мадэлі для загрузкі з HuggingFace (напрыклад, 'nvidia/stt_be_fastconformer_hybrid_large_pc')
        :param att_context_size: памер кантэксту ўвагі (напрыклад, [128, 128]), выкарыстоўваецца для змены мадэлі ўвагі на 'rel_pos_local_attn'.
        Карысна для апрацоўкі доўгіх аўдыяфайлаў - тады трэба ставіць [128, 128] ці [256, 256] каб не чытаць увесь файл у памяць адразу.
        Для кароткіх аўдыяфайлаў можна не ўказваць, тады будзе выкарыстоўвацца стандартная мадэль увагі.
        """
        MODEL_LOADERS = {
            "nvidia/stt_be_fastconformer_hybrid_large_pc": lambda: nemo_asr.models.EncDecHybridRNNTCTCBPEModel.from_pretrained(
                model_name="nvidia/stt_be_fastconformer_hybrid_large_pc"),
            "nvidia/stt_be_conformer_transducer_large": lambda: nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(
                model_name="nvidia/stt_be_conformer_transducer_large"),
            "nvidia/stt_be_conformer_ctc_large": lambda: nemo_asr.models.EncDecCTCModelBPE.from_pretrained(
                model_name="nvidia/stt_be_conformer_ctc_large")
        }

        if model_name in MODEL_LOADERS:
            self._asr_model = MODEL_LOADERS[model_name]()
            if att_context_size:
                self._asr_model.change_attention_model(
                    self_attention_model="rel_pos_local_attn",
                    att_context_size=att_context_size  # памер кантэксту (акна) увагі
                )
        else:
            available_models = ", ".join(MODEL_LOADERS.keys())
            raise ValueError(
                f"Памылка: мадэль '{model_name}' невядомая. "
                f"Даступныя варыянты: [{available_models}]"
            )

        self.batch_size = batch_size

        # адпраўляем канвеер на GPU (калі даступна)
        if os.getenv("TORCH_DEVICE"):
            self._asr_model.to(torch.device(os.getenv("TORCH_DEVICE")))

    def transcript_file(self, audio_file_path: str) -> str:
        """
        Распазнае ўвесь аўдыяфайл.
        :param audio_file_path: Шлях да аўдыяфайла.
        :return: Распазнаны тэкст для ўсяго файла.
        """
        audio_data = VoiceFile.read_wav(audio_file_path)

        output = self._asr_model.transcribe(audio_data, batch_size=self.batch_size)
        if len(output) != 1:
            raise RuntimeError(f"Expected 1 transcription, but got {len(output)}")
        return output[0].text

    def transcript_parts(self, data: VoiceFile) -> None:
        """
        Распазнае пэўныя сегменты(часткі) аўдыяфайла.
        :param data: аб'ект VoiceFile, які змяшчае шлях да аўдыяфайла і сегменты для распазнавання.
        """
        audio_data = VoiceFile.read_wav(data.audio_file_path)

        real_segments = []
        audios = []
        for segment in data.segments:
            if segment.end - segment.start >= 0.2:  # толькі часткі даўжэйшыя за 0.2 секунды
                real_segments.append(segment)
                sample_rate = 16000
                start_sample = int(segment.start * sample_rate)
                end_sample = int(segment.end * sample_rate)
                # бяром патрэбны кавалак
                part = audio_data[start_sample:end_sample]
                audio_tensor = torch.from_numpy(part)
                audios.append(audio_tensor)

        transcriptions = self._asr_model.transcribe(audios, batch_size=self.batch_size)

        if len(transcriptions) != len(audios):
            raise RuntimeError(f"Expected {len(audios)} transcriptions, but got {len(transcriptions)}")

        for segment, transcription in zip(real_segments, transcriptions):
            segment.plain_text = transcription.text

    def transcript_part(self, data: VoiceFile, segment: VoicePart) -> None:
        """
        Робіць транскрыпт для аднаго сегмента.
        """
        audio_data = VoiceFile.read_wav(data.audio_file_path, segment.start, segment.end)
        audio_tensor = torch.from_numpy(audio_data)
        transcriptions = self._asr_model.transcribe([audio_tensor], batch_size=self.batch_size)

        if len(transcriptions) != 1:
            raise RuntimeError(f"Expected 1 transcription, but got {len(transcriptions)}")

        segment.text = transcriptions[0].text
