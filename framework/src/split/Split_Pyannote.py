from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from SplitData import VoiceFile, VoicePart, IAudioSplitter


class Split_Pyannote(IAudioSplitter):
    """
    Разбівае аўдыяфайл на часткі, якія ўтрымліваюць маўленне, выкарыстоўваючы https://github.com/pyannote/pyannote-audio.
    """

    def __init__(self):
        # Community-1 open-source speaker diarization pipeline
        self._pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=True)
        # send pipeline to GPU (when available)
        # pipeline.to(torch.device("cuda"))

    def split(self, audio_file_path: str) -> VoiceFile:
        with ProgressHook() as hook:
            output = self._pipeline(audio_file_path, hook=hook)

        data = VoiceFile(audio_file_path)
        data.segments = [VoicePart(start=turn.start, end=turn.end, speaker_id=speaker)
                         for turn, speaker in output.exclusive_speaker_diarization]
        return data
