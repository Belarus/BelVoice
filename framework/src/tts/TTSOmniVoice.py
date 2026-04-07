"""
Робіць TTS праз https://github.com/k2-fsa/OmniVoice.
"""

from omnivoice import OmniVoice
import torchaudio
import os


class TTSOmniVoice:

    def __init__(self):
        self._model = OmniVoice.from_pretrained("k2-fsa/OmniVoice")

    def tts(self, text: str, output_file: str):
        audio = self._model.generate(
            text=text,
            language="be",
            ref_audio=os.path.join(os.path.dirname(__file__), "tts-omnivoice/ref.wav"),
            ref_text="Аднак калі паглядзелі малінаўцы, якія спраўныя ды гладкія сталі коні ў Юстыні, як добра ядуць каровы і нават жытнюю салому, калі ператрасеш яе з канюшынай, то самі кінуліся шукаць насенне і сеяць канюшыну."
        )

        torchaudio.save(output_file, audio[0], self._model.sampling_rate)
