import docker
import os
import tempfile
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download, constants

class TTSCoquiTTS:
    def __init__(self):
        self._client = docker.from_env()

        base = os.path.dirname(__file__)
        dockerfile_path = os.path.join(base, "tts-coqui-docker")
        print("docker path="+dockerfile_path)

        print("build image...")
        self._image, logs = self._client.images.build(
            path=dockerfile_path
        )

        for line in logs:
            if 'stream' in line:
                print(line['stream'], end='')
            elif 'error' in line:
                print(f"ПАМЫЛКА: {line['error']}")

        self._models_path = snapshot_download(repo_id="alex73/BelarusianTTSviaCoquiTTS")
        print(f"Мадэлі спампаваліся ў {self._models_path}")
        self._models_relative_path = Path(self._models_path).relative_to(Path(constants.HF_HUB_CACHE))

    def tts(self, text: str, output_file_path: str):
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(os.path.join(tmpdirname, "in.txt"), "w") as f:
                f.write(text)

            print("run container")
            mp = self._models_relative_path
            logs = self._client.containers.run(
                self._image,
                entrypoint = f"python3 TTS/server/convert.py --config_path /m/{mp}/glowtts/config.json --model_path /m/{mp}/glowtts/*.pth --vocoder_config_path /m/{mp}/hifigan/config.json --vocoder_path /m/{mp}/hifigan/*.pth",
                volumes = {constants.HF_HUB_CACHE : {'bind': '/m', 'mode': 'ro'}, tmpdirname: {'bind': '/fan/', 'mode': 'rw'}}
            )
            print(logs.decode('utf-8'))
            shutil.move(os.path.join(tmpdirname, "result.wav"), output_file_path)
