import os

import torch
from pyannote.audio import Model
from pyannote.audio import Pipeline
from pyannote.audio.pipelines import VoiceActivityDetection
from pyannote.audio.pipelines.utils.hook import ProgressHook

from .SplitData import VoiceFile, VoicePart


class Split_Pyannote:
    """
    Разбівае аўдыяфайл на часткі, якія ўтрымліваюць маўленне, выкарыстоўваючы https://github.com/pyannote/pyannote-audio.

    Усярэдзіне pyannote/speaker-diarization-community-1 знаходзіцца мадэль pyannote/segmentation-3.0 - гэта
    выяўлена параўнаннем файлаў. Таму, для простай сегментацыі без спікераў лепш выкарыстоўваць яе.
    """

    def __init__(self, segmentation_only=True):
        self._segmentation_only = segmentation_only
        if self._segmentation_only:
            # 1. Загружаем толькі мадэль сегментацыі
            self._model = Model.from_pretrained("pyannote/segmentation-3.0", token=True)

            # 2. Ствараем пайплайн менавіта для VAD на базе гэтай мадэлі
            self._pipeline = VoiceActivityDetection(segmentation=self._model)
            # 3. Наладжваем параметры (парогі і мінімальную працягласць)
            # Налады дэтэкцыі (onset / offset)
            self._pipeline.onset = 0.5  # пакідаем аптымальны стандартны парог для выяўлення сувязнага маўлення
            self._pipeline.offset = 0.4  # крыху больш нізкі парог для заканчэння, каб не абразаць ціхія канчаткі слоў ці згасанне спеваў
            HYPER_PARAMETERS = {
                "min_duration_on": 3,  # не ствараць фрагменты карацейшыя за 1.5 сек
                "min_duration_off": 0.3  # аб'ядноўваць паўзы, карацейшыя за 3.0 сек
            }
            self._pipeline.instantiate(HYPER_PARAMETERS)
        else:
            # Community-1 open-source speaker diarization pipeline
            self._pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=True)

        # send pipeline to GPU (when available)
        if os.getenv("TORCH_DEVICE"):
            self._pipeline.to(torch.device(os.getenv("TORCH_DEVICE")))

    def split(self, audio_file_path: str) -> VoiceFile:
        if self._segmentation_only:
            # Пайплайн сам зробіць і inference, і агрэгацыю, і бінарызацыю
            speech_annotation = self._pipeline(audio_file_path)

            data = VoiceFile(audio_file_path)
            data.segments = [
                # get_timeline().support() злучае накладзеныя адзін на аднаго сегменты
                VoicePart(start=segment.start, end=segment.end)
                for segment in speech_annotation.get_timeline().support()
            ]
        else:
            with ProgressHook() as hook:
                output = self._pipeline(audio_file_path, hook=hook)

            data = VoiceFile(audio_file_path)
            data.segments = [VoicePart(start=turn.start, end=turn.end, speaker_id=speaker)
                             for turn, speaker in output.exclusive_speaker_diarization]

        durations = [part.end - part.start for part in data.segments]
        import statistics
        if durations:
            print(f"Знойдзена фрагментаў маўлення: {len(durations)}")
            print(f"Мінімальная працягласць: {min(durations):.2f} сек")
            print(f"Максімальная працягласць: {max(durations):.2f} сек")
            print(f"Сярэдняя працягласць (Mean): {statistics.mean(durations):.2f} сек")
            print(f"Медыяна (Median): {statistics.median(durations):.2f} сек")
            print(f"Агульны час маўлення: {sum(durations):.2f} сек")

        return data
