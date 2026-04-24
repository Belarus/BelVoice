import subprocess
from typing import List

import numpy as np
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

from split.SplitData import VoiceFile


class ASR_Facebook:
    """
    Глядзі спіс мадэляў на https://github.com/facebookresearch/omnilingual-asr
    Найлепшыя вынікі дае omniASR_LLM_Unlimited_*_v2
    """

    def __init__(self, model_card: str = "omniASR_LLM_Unlimited_300M_v2", lang: str = "bel_Cyrl", batch_size: int = 1):
        self._pipeline = ASRInferencePipeline(model_card)
        self._lang = lang
        self._batch_size = batch_size

    def transcript_file(self, audio_file_path: str) -> List[str]:
        transcriptions = self._pipeline.transcribe([audio_file_path], lang=[self._lang], batch_size=self._batch_size)
        if len(transcriptions) != 1:
            raise RuntimeError(f"Expected only one text, but got {len(transcriptions)}")
        return transcriptions[0]

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
                part = audio_data[start_sample:end_sample]
                audios.append({"waveform": part, "sample_rate": 16000})

        transcriptions = self._pipeline.transcribe(audios, lang=[self._lang] * len(audios), batch_size=self._batch_size)

        if len(transcriptions) != len(audios):
            raise RuntimeError(f"Expected {len(audios)} transcriptions, but got {len(transcriptions)}")

        for segment, transcription in zip(real_segments, transcriptions):
            segment.plain_text = transcription
