import io
import os
import subprocess
from typing import Optional, Literal

import litellm
import numpy as np
from scipy.io import wavfile

from split.SplitData import VoiceFile


class ASR_Gemini:
    """
    See models list on the https://models.litellm.ai/
    Usually, you need to set LLM's token into some env variable.
    Выкарыстоўвайце толькі назвы мадэляў, якія пачынаюцца з 'gemini/'. Напрыклад, 'gemini/gemini-3-flash-preview'.
    """

    PROMPT = """
    Generate a transcript of this Belarusian language audio. Avoid any preambles.
    """

    def __init__(self, model_name: str, prompt: str = PROMPT,
                 thinking_level: Optional[Literal["none", "minimal", "low", "medium", "high"]] = "none") -> None:
        if not model_name.startswith("gemini/"):
            raise Exception(
                f"{model_name} - не мадэль Gemini. Падтрымліваюцца толькі Gemini каб мець магчымасць запампаваць файл на Google для распазнавання.")
        if os.environ.get("GEMINI_API_KEY") is None:
            raise Exception("Памылка: не ўстаноўлены GEMINI_API_KEY у якасці зменнай асяроддзя.")

        self._model_name = model_name
        self._prompt = prompt
        self._thinking_level = thinking_level

    def transcript_file(self, audio_file_path: str) -> str:
        pl = audio_file_path.lower()
        if pl.endswith(".wav"):
            mime_type = "audio/x-wav"
        elif pl.endswith(".mp3"):
            mime_type = "audio/mpeg"
        elif pl.endswith(".aiff"):
            mime_type = "audio/x-aiff"
        elif pl.endswith(".aac"):
            mime_type = "audio/aac"
        elif pl.endswith(".ogg"):
            mime_type = "audio/ogg"
        elif pl.endswith(".opus"):
            mime_type = "audio/ogg"
        elif pl.endswith(".flac"):
            mime_type = "audio/flac"
        else:
            raise Exception(
                f"{audio_file_path} - невядомы фармат аўдыё. Падтрымліваюцца файлы з пашырэннямі .wav, .mp3, .aiff, .aac, .ogg, .opus, .flac.")

        # upload file
        audio_file = litellm.create_file(file=audio_file_path,
                                         custom_llm_provider="gemini", purpose="user_data")

        response = litellm.completion(
            model=self._model_name,
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": self._prompt
                }, {
                    "type": "file",
                    "file": {"file_id": audio_file.id, "format": mime_type}
                }]
            }],
            temperature=0.0,
            reasoning_effort=self._thinking_level
        )

        # delete file
        litellm.file_delete(audio_file.id, custom_llm_provider="gemini")

        return response.choices[0].message.content

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

        for segment in data.segments:
            if segment.end - segment.start >= 0.2:  # толькі часткі даўжэйшыя за 0.2 секунды
                sample_rate = 16000
                start_sample = int(segment.start * sample_rate)
                end_sample = int(segment.end * sample_rate)
                # бяром патрэбны кавалак
                part = audio_data[start_sample:end_sample]

                byte_io = io.BytesIO()
                wavfile.write(byte_io, sample_rate, part)
                wav_bytes = byte_io.getvalue()

                audio_file = litellm.create_file(file=('audio.wav', wav_bytes), custom_llm_provider="gemini",
                                                 purpose="user_data")

                response = litellm.completion(
                    model=self._model_name,
                    messages=[{
                        "role": "user",
                        "content": [{
                            "type": "text",
                            "text": self._prompt
                        }, {
                            "type": "file",
                            "file": {"file_id": audio_file.id, "format": "audio/x-wav"}
                        }]
                    }],
                    temperature=0.0,
                    reasoning_effort=self._thinking_level
                )
                # delete file
                litellm.file_delete(audio_file.id, custom_llm_provider="gemini")

                segment.plain_text = response.choices[0].message.content
