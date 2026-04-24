import numpy
import subprocess
import torch
from SplitData import VoiceFile, VoicePart, IAudioSplitter
from silero_vad import load_silero_vad, get_speech_timestamps


class Split_SileroVAD(IAudioSplitter):
    """
    Разбівае аўдыяфайл на часткі, якія ўтрымліваюць маўленне, выкарыстоўваючы мадэль SileroVAD.
    """

    def __init__(self):
        self._model = load_silero_vad()

    def split(self, audio_file_path: str,
              threshold: float = 0.5,
              min_speech_duration_ms: int = 250,
              max_speech_duration_s: float = float('inf'),
              min_silence_duration_ms: int = 100,
              speech_pad_ms: int = 30,
              visualize_probs: bool = False,
              neg_threshold: float = None,
              min_silence_at_max_speech: int = 98,
              use_max_poss_sil_at_max_speech: bool = True
              ) -> VoiceFile:
        """
            Аўдыё можа быць у любым фармаце, які падтрымлівае ffmpeg.
            Параметры з Silero VAD:
            -----------------------
            threshold: float (default - 0.5)
                Speech threshold. Silero VAD outputs speech probabilities for each audio chunk, probabilities ABOVE this value are considered as SPEECH.
                It is better to tune this parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets.

            min_speech_duration_ms: int (default - 250 milliseconds)
                Final speech chunks shorter min_speech_duration_ms are thrown out

            max_speech_duration_s: int (default -  inf)
                Maximum duration of speech chunks in seconds
                Chunks longer than max_speech_duration_s will be split at the timestamp of the last silence that lasts more than 100ms (if any), to prevent aggressive cutting.
                Otherwise, they will be split aggressively just before max_speech_duration_s.

            min_silence_duration_ms: int (default - 100 milliseconds)
                In the end of each speech chunk wait for min_silence_duration_ms before separating it

            speech_pad_ms: int (default - 30 milliseconds)
                Final speech chunks are padded by speech_pad_ms each side

            visualize_probs: bool (default - False)
                whether draw prob hist or not

            neg_threshold: float (default = threshold - 0.15)
                Negative threshold (noise or exit threshold). If model's current state is SPEECH, values BELOW this value are considered as NON-SPEECH.

            min_silence_at_max_speech: int (default - 98ms)
                Minimum silence duration in ms which is used to avoid abrupt cuts when max_speech_duration_s is reached

            use_max_poss_sil_at_max_speech: bool (default - True)
                Whether to use the maximum possible silence at max_speech_duration_s or not. If not, the last silence is used.
            """
        wav = self._read_audio(audio_file_path)
        timestamps = get_speech_timestamps(wav, self._model, return_seconds=True,
                                      time_resolution=3,
                                      threshold=threshold,
                                      min_speech_duration_ms=min_speech_duration_ms,
                                      max_speech_duration_s=max_speech_duration_s,
                                      min_silence_duration_ms=min_silence_duration_ms,
                                      speech_pad_ms=speech_pad_ms,
                                      visualize_probs=visualize_probs,
                                      neg_threshold=neg_threshold,
                                      min_silence_at_max_speech=min_silence_at_max_speech,
                                      use_max_poss_sil_at_max_speech=use_max_poss_sil_at_max_speech)
        data = VoiceFile(audio_file_path)
        data.segments = [VoicePart(start=item['start'], end=item['end']) for item in timestamps]
        return data

    def _read_audio(self, path: str, sampling_rate: int = 16000):
        # Каманда ffmpeg для атрымання сырых (raw) PCM f32le дадзеных праз stdout
        # -f f32le: фармат float 32-bit little endian (зручна для torch)
        # -ac 1: мона
        # -ar: частата дыскрэтызацыі
        cmd = [
            'ffmpeg', '-v', 'error',
            '-i', path,
            '-f', 'f32le',
            '-ac', '1',
            '-ar', str(sampling_rate),
            '-'
        ]

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise Exception(f"ffmpeg error: {stderr.decode()}")
            # Канвертуем атрыманыя байты ў масіў numpy (float32)
            samples = numpy.frombuffer(stdout, dtype=numpy.float32).copy()
            return torch.from_numpy(samples)
        except Exception as e:
            raise Exception(f"Памылка пры чытанні праз ffmpeg: {e}")
