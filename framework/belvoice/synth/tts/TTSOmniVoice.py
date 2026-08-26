"""
Робіць TTS праз https://github.com/k2-fsa/OmniVoice.
"""

from omnivoice import OmniVoice
import torchaudio
import torch
import os


class TTSOmniVoice:

    def __init__(self):
        self._model = OmniVoice.from_pretrained("k2-fsa/OmniVoice")

    def tts(self, text: str, output_file: str):
        audio = self._model.generate(
            text=text,
            language="be",
            ref_audio=os.path.join(os.path.dirname(__file__), "tts-omnivoice/ref.wav"),
            ref_text="Адна́к калі́ паглядзе́лі малі́наўцы, які́я спра́ўныя ды гла́дкія ста́лі ко́ні ў Юсты́ні, як до́бра яду́ць каро́вы і на́ват жы́тнюю сало́му, калі́ ператрасе́ш яе́ з канюшы́най, то са́мі кі́нуліся шука́ць насе́нне і се́яць канюшы́ну."
        )
        # Пераўтварэнне numpy-масіва ў torch-тэнзар
        audio_tensor = torch.from_numpy(audio[0])
        # torchaudio патрабуе 2D тэнзар віду [каналы, сэмплы]
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor.unsqueeze(0)

        torchaudio.save(output_file, audio_tensor, self._model.sampling_rate)
