import argparse
import io
import os
import subprocess
import sys
from datetime import datetime
import pytz
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer


def create_argparser():
    def convert_boolean(x):
        return x.lower() in ["true", "1", "yes"]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list_models",
        type=convert_boolean,
        nargs="?",
        const=True,
        default=False,
        help="list available pre-trained tts and vocoder models.",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="tts_models/en/ljspeech/tacotron2-DDC",
        help="Name of one of the pre-trained tts models in format <language>/<dataset>/<model_name>",
    )
    parser.add_argument("--vocoder_name", type=str, default=None, help="name of one of the released vocoder models.")

    # Args for running custom models
    parser.add_argument("--config_path", default=None, type=str, help="Path to model config file.")
    parser.add_argument(
        "--model_path",
        type=str,
        default=None,
        help="Path to model file.",
    )
    parser.add_argument(
        "--vocoder_path",
        type=str,
        help="Path to vocoder model file. If it is not defined, model uses GL as vocoder. Please make sure that you installed vocoder library before (WaveRNN).",
        default=None,
    )
    parser.add_argument("--vocoder_config_path", type=str, help="Path to vocoder model config file.", default=None)
    parser.add_argument("--speakers_file_path", type=str, help="JSON file for multi-speaker model.", default=None)
    parser.add_argument("--port", type=int, default=5002, help="port to listen on.")
    parser.add_argument("--use_cuda", type=convert_boolean, default=False, help="true to use CUDA.")
    parser.add_argument("--debug", type=convert_boolean, default=False, help="true to enable Flask debug mode.")
    parser.add_argument("--show_details", type=convert_boolean, default=False, help="Generate model detail page.")
    return parser


# parse the args
args = create_argparser().parse_args()
print(f"args={args}")

path = "/root/TTS/.models.json"
manager = ModelManager(path)

if args.list_models:
    manager.list_models()
    sys.exit()

# update in-use models to the specified released models.
model_path = None
config_path = None
speakers_file_path = None
vocoder_path = None
vocoder_config_path = None

# CASE1: list pre-trained TTS models
if args.list_models:
    manager.list_models()
    sys.exit()

# CASE2: load pre-trained model paths
if args.model_name is not None and not args.model_path:
    model_path, config_path, model_item = manager.download_model(args.model_name)
    args.vocoder_name = model_item["default_vocoder"] if args.vocoder_name is None else args.vocoder_name

if args.vocoder_name is not None and not args.vocoder_path:
    vocoder_path, vocoder_config_path, _ = manager.download_model(args.vocoder_name)

# CASE3: set custom model paths
if args.model_path is not None:
    model_path = args.model_path
    config_path = args.config_path
    speakers_file_path = args.speakers_file_path

if args.vocoder_path is not None:
    vocoder_path = args.vocoder_path
    vocoder_config_path = args.vocoder_config_path

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
    use_cuda=args.use_cuda,
)

use_multi_speaker = hasattr(synthesizer.tts_model, "num_speakers") and (
    synthesizer.tts_model.num_speakers > 1 or synthesizer.tts_speakers_file is not None
)
speaker_manager = getattr(synthesizer.tts_model, "speaker_manager", None)

use_multi_language = hasattr(synthesizer.tts_model, "num_languages") and (
    synthesizer.tts_model.num_languages > 1 or synthesizer.tts_languages_file is not None
)
language_manager = getattr(synthesizer.tts_model, "language_manager", None)

# TODO: set this from SpeakerManager
use_gst = synthesizer.tts_config.get("use_gst", False)


def allowed_time() -> bool:
    return True
#    h = datetime.now(pytz.timezone('Europe/Minsk')).hour
#    return h >= 23 or h < 9


def status(dir: str, message: str):
    print(message)
    with open(dir + "/status.txt", 'w') as file:
        file.write(message)


def process_old(dir: str):
    print(f"Processing {dir}...")
    with open(dir + "/in.txt", 'r') as file:
        text = file.read()
    sens = synthesizer.split_into_sentences(text)
    for i in range(len(sens)):
        if not allowed_time():
            print(f"Not allowed time: {datetime.now(pytz.timezone('Europe/Minsk'))}")
            return
        fn = dir + "/temp/" + str(i).zfill(8) + ".wav"
        if not os.path.exists(fn):
            wavs = synthesizer.tts(sens[i], split_sentences=False)
            out = io.BytesIO()
            synthesizer.save_wav(wavs, out)
            with open(fn, "wb") as f:
                f.write(out.getbuffer())
            status(dir, f"Агучка: зроблена {round(i * 100 / len(sens))}%")
    status(dir, "Збіранне выніковага файла...")
    with open(dir + "/temp/concat.ls", 'w') as file:
        for i in range(len(sens)):
            fn = str(i).zfill(8) + ".wav"
            file.write(f"file '{fn}'\n")
    subprocess.call(['ffmpeg', '-f', 'concat', '-i', dir + "/temp/concat.ls", dir + "/result.opus"])
    status(dir, "Гатова")
    tmp = dir + "/temp/"
    for ls in os.listdir(dir + "/temp/"):
        f = tmp + ls
        os.remove(f)
    os.rmdir(tmp)

def process(text_file: str, output_file: str):
    with open(text_file, 'r') as file:
        text = file.read()
    wavs = synthesizer.tts(text, split_sentences=False)
    out = io.BytesIO()
    synthesizer.save_wav(wavs, out)
    with open(output_file, "wb") as f:
        f.write(out.getbuffer())

os.makedirs("/fan/temp", exist_ok=True)
process("/fan/in.txt", "/fan/result.wav")
