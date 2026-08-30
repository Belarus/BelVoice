"""
Робіць TTS праз https://github.com/k2-fsa/OmniVoice.
"""

from omnivoice import OmniVoice
from collections.abc import Callable
import torchaudio
import torch
import os
import re
import subprocess

# Разбівае тэкст на сказы: кожны сказ уключае наступны за ім знак прыпынку (. ! ?)
# і прабельныя сімвалы пасля яго, каб сума даўжынь усіх сказаў дакладна складала len(text).
_SENTENCE_PATTERN = re.compile(r"[^.!?]*[.!?]+\s*|[^.!?]+$", re.DOTALL)


_REF_TEXT = ("Адна́к калі́ паглядзе́лі малі́наўцы, які́я спра́ўныя ды гла́дкія ста́лі ко́ні ў Юсты́ні, "
             "як до́бра яду́ць каро́вы і на́ват жы́тнюю сало́му, калі́ ператрасе́ш яе́ з канюшы́най, "
             "то са́мі кі́нуліся шука́ць насе́нне і се́яць канюшы́ну.")
_REF_AUDIO = os.path.join(os.path.dirname(__file__), "tts-omnivoice/ref.wav")


class TTSOmniVoice:
    """
    Агучвае тэкст па сказах.
    """

    def __init__(self,
                 split_sentences: bool = False
                 ):
        self._model = OmniVoice.from_pretrained("k2-fsa/OmniVoice")
        self._split_sentences = split_sentences
        self._voice_prompt = self._model.create_voice_clone_prompt(
            ref_audio=_REF_AUDIO,
            ref_text=_REF_TEXT
        )

    def tts(self, text: str, output_file: str, callback: Callable[[float], None] | None = None):
        if not self._split_sentences:
            self._synthesize(text, output_file)
            if callback:
                callback(100.0)
            return

        sentences = [m.group() for m in _SENTENCE_PATTERN.finditer(text)] if text else []

        total_len = len(text)
        if total_len == 0 or not any(s.strip() for s in sentences):
            if callback:
                callback(100.0)
            return

        sentence_files = []
        processed_len = 0
        try:
            if callback:
                callback(0.0)
            for i, sentence in enumerate(sentences):
                processed_len += len(sentence)

                if sentence.strip():
                    sentence_file = f"{output_file}.{i:06d}.wav"
                    self._synthesize(sentence, sentence_file)
                    sentence_files.append(sentence_file)

                if callback:
                    callback(processed_len / total_len * 100.0)

            self._concat_wavs(sentence_files, output_file)
        finally:
            for sentence_file in sentence_files:
                if os.path.exists(sentence_file):
                    os.remove(sentence_file)

    def _synthesize(self, text: str, output_file: str):
        """
        Генеруе аўдыё для аднаго фрагменту тэксту і захоўвае яго ў файл.
        """
        audio = self._model.generate(
            text=text,
            language="be",
            voice_clone_prompt=self._voice_prompt
        )
        # Пераўтварэнне numpy-масіва ў torch-тэнзар
        audio_tensor = torch.from_numpy(audio[0])
        # torchaudio патрабуе 2D тэнзар віду [каналы, сэмплы]
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor.unsqueeze(0)

        torchaudio.save(output_file, audio_tensor, self._model.sampling_rate)


    def _concat_wavs(self, wav_files: list[str], output_file: str):
        """
        Злучае некалькі wav-файлаў у адзін праз ffmpeg (concat demuxer).
        """
        list_file = f"{output_file}.concat.txt"
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for wav_file in wav_files:
                    f.write(f"file '{os.path.abspath(wav_file)}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_file
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)
