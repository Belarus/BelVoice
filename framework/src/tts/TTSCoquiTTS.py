import os
import tempfile
import shutil
import io
from pathlib import Path
from huggingface_hub import snapshot_download, constants
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer

class TTSCoquiTTS:
    def __init__(self):
        self._models_path = snapshot_download(repo_id="alex73/BelarusianTTSviaCoquiTTS")
        self._models_relative_path = Path(self._models_path).relative_to(Path(constants.HF_HUB_CACHE))

    def tts(self, text: str, output_file_path: str):
        mp = self._models_relative_path
        self._convert(text, output_file_path)
            # logs = self._client.containers.run(
            #     self._image,
            #     entrypoint = f"python3 TTS/server/convert.py --config_path /m/{mp}/glowtts/config.json --model_path /m/{mp}/glowtts/*.pth --vocoder_config_path /m/{mp}/hifigan/config.json --vocoder_path /m/{mp}/hifigan/*.pth",
            #     volumes = {constants.HF_HUB_CACHE : {'bind': '/m', 'mode': 'ro'}, tmpdirname: {'bind': '/fan/', 'mode': 'rw'}}
            # )
            # print(logs.decode('utf-8'))
            # shutil.move(os.path.join(tmpdirname, "result.wav"), output_file_path)

    def _convert(self, text: str, output_file_path: str):

        path =None# "/root/TTS/.models.json"
        manager = ModelManager(path)

        # update in-use models to the specified released models.
        model_path = None
        config_path = None
        speakers_file_path = None
        vocoder_path = None
        vocoder_config_path = None

        model_path = f"{self._models_path}/glowtts/best_model_23590.pth"
        config_path = f"{self._models_path}/glowtts/config.json"
        speakers_file_path = None

        vocoder_path = f"{self._models_path}/hifigan/best_model_163888.pth"
        vocoder_config_path = f"{self._models_path}/hifigan/config.json"

        # load models
        synthesizer = Synthesizer(
            tts_checkpoint=model_path,
            tts_config_path=config_path,
            tts_speakers_file=speakers_file_path,
            tts_languages_file=None,
            vocoder_checkpoint=vocoder_path,
            vocoder_config=vocoder_config_path,
            encoder_checkpoint="",
            encoder_config="",
            use_cuda=None
        )

        use_multi_speaker = None
        speaker_manager = None

        use_multi_language = None
        language_manager = None

        # TODO: set this from SpeakerManager
        use_gst = synthesizer.tts_config.get("use_gst", False)

        wavs = synthesizer.tts(text, split_sentences=False)
        out = io.BytesIO()
        synthesizer.save_wav(wavs, out)
        with open(output_file_path, "wb") as f:
            f.write(out.getbuffer())
