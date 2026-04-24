import subprocess

import nemo.collections.asr as nemo_asr
import numpy as np
import torch

from split.SplitData import VoiceFile


class ASR_Nvidia:
    """
    See models list on the https://huggingface.co/nvidia/models?search=stt_be
    """

    def __init__(self, model_name: str):
        MODEL_LOADERS = {
            "nvidia/stt_be_fastconformer_hybrid_large_pc": lambda: nemo_asr.models.EncDecHybridRNNTCTCBPEModel.from_pretrained(
                model_name="nvidia/stt_be_fastconformer_hybrid_large_pc"),
            "nvidia/stt_be_conformer_transducer_large": lambda: nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(
                "nvidia/stt_be_conformer_transducer_large"),
            "nvidia/stt_be_conformer_ctc_large": lambda: nemo_asr.models.EncDecCTCModelBPE.from_pretrained(
                "nvidia/stt_be_conformer_ctc_large")
        }

        if model_name in MODEL_LOADERS:
            self._asr_model = MODEL_LOADERS[model_name]()
        else:
            available_models = ", ".join(MODEL_LOADERS.keys())
            raise ValueError(
                f"Памылка: мадэль '{model_name}' невядомая. "
                f"Даступныя варыянты: [{available_models}]"
            )

    def transcript_file(self, audio_file_path: str) -> str:
        output = self._asr_model.transcribe([audio_file_path])
        if len(output) != 1:
            raise RuntimeError(f"Expected 1 transcription, but got {len(output)}")
        return output[0].text

    def transcript_parts(self, data: VoiceFile) -> None:
        # чытаем увесь файл як PCM f32le, 16kHz, mono
        command = [
            'ffmpeg',
            '-i', data.audio_file_path,
            '-f', 'f32le',
            '-ar', '16000',
            '-ac', '1',
            'pipe:1'
        ]
        process = subprocess.run(command, capture_output=True)
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {process.stderr.decode()}")

        # канвертуем байты ў numpy array (float32)
        audio_data = np.frombuffer(process.stdout, dtype=np.float32)

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

        transcriptions = self._asr_model.transcribe(audios)

        if len(transcriptions) != len(audios):
            raise RuntimeError(f"Expected {len(audios)} transcriptions, but got {len(transcriptions)}")

        for segment, transcription in zip(real_segments, transcriptions):
            segment.plain_text = transcription.text
