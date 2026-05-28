#
# Тут знаходзіцца код для разбіўкі аўдыяфайла на часткі, вызначэння спікераў, распазнавання маўлення.
# Гэта дазваляе распазнаваць маўленне з пазнакамі часу і спікераў, напрыклад, для субцітраў ці корпусу.
#
import json


class VoicePart:
    """
    Утрымлівае інфармацыю пра адну частку аўдыяфайла (маўленне аднаго чалавека без паўзы).
    """

    start: float  # пачатак маўленчага фрагмента ў секундах
    end: float  # канец маўленчага фрагмента ў секундах
    speaker_id: str  # хто гаворыць
    plain_text: str  # распазнаны тэкст без апрацоўкі
    optimized_text: str  # нармалізаваны або адкарэктаваны тэкст

    def __init__(self,
                 start: float = None,
                 end: float = None,
                 speaker_id: str = None,
                 plain_text: str = None,
                 optimized_text: str = None) -> None:
        self.start = start
        self.end = end
        self.speaker_id = speaker_id
        self.plain_text = plain_text
        self.optimized_text = optimized_text

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "speaker_id": getattr(self, "speaker_id", None),
            "plain_text": getattr(self, "plain_text", None),
            "optimized_text": getattr(self, "optimized_text", None)
        }

    @staticmethod
    def from_dict(data: dict) -> 'VoicePart':
        part = VoicePart()
        part.start = data.get("start")
        part.end = data.get("end")
        part.speaker_id = data.get("speaker_id")
        part.plain_text = data.get("plain_text", None)
        part.optimized_text = data.get("optimized_text", None)
        return part


class VoiceFile:
    """
    Утрымлівае інфармацыю пра ўсе часткі аўдыяфайла.
    """

    def __init__(self, audio_file_path: str) -> None:
        self.audio_file_path = audio_file_path
        self.segments: list[VoicePart] = []

    def to_string(self) -> str:
        data = {
            "audio_file_path": self.audio_file_path,
            "segments": [part.to_dict() for part in self.segments]
        }
        return json.dumps(data, ensure_ascii=False, indent=4)

    def save_to_json(self, json_path: str) -> None:
        data = {
            "audio_file_path": self.audio_file_path,
            "segments": [part.to_dict() for part in self.segments]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def dump_stat(self) -> None:
        import statistics

        durations = [part.end - part.start for part in self.segments]
        if durations:
            p10 = statistics.quantiles(durations, n=10)
            print(
                f"Працягласць маўлення: {len(self.segments)} сегментаў {min(durations):.2f}-{max(durations):.2f} с, медыяна: {statistics.median(durations):.2f} с, 10/90%: {p10[0]:.2f}/{p10[-1]:.2f}")
        else:
            print("Няма сегментаў маўлення")

        pauses = []
        for i in range(1, len(self.segments)):
            pause = self.segments[i].start - self.segments[i - 1].end
            pauses.append(pause)

        if pauses:
            p10 = statistics.quantiles(pauses, n=10)
            print(
                f"Працягласць паўз: {min(pauses):.2f}-{max(pauses):.2f} с, медыяна: {statistics.median(pauses):.2f} с, 10/90%: {p10[0]:.2f}/{p10[-1]:.2f}")
        else:
            print("Няма паўз")

    @staticmethod
    def dump_stats(files: list[VoiceFile]) -> None:
        import statistics

        durations = []
        pauses = []
        for f in files:
            for part in f.segments:
                durations.append(part.end - part.start)

            for i in range(1, len(f.segments)):
                pause = f.segments[i].start - f.segments[i - 1].end
                pauses.append(pause)

        p10 = statistics.quantiles(durations, n=10)
        print(
            f"Агульная працягласць маўлення: {len(durations)} сегментаў, {min(durations):.2f}-{max(durations):.2f} с, медыяна: {statistics.median(durations):.2f} с, 10/90%: {p10[0]:.2f}/{p10[-1]:.2f} ")

        p10 = statistics.quantiles(pauses, n=10)
        print(
            f"Агульная працягласць паўз: {min(pauses):.2f}-{max(pauses):.2f} с, медыяна: {statistics.median(pauses):.2f} с, 10/90%: {p10[0]:.2f}/{p10[-1]:.2f}")

    @staticmethod
    def load_from_json(json_path: str) -> 'VoiceFile':
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        obj = VoiceFile(data.get("audio_file_path"))
        obj.segments = [VoicePart.from_dict(p) for p in data.get("segments", [])]

        prev_end = None
        for part in obj.segments:
            if part.start is None:
                raise ValueError(f"Памылка пры загрузцы {json_path}: адсутнічае поле 'start' у адным з сегментаў")
            if part.end is None:
                raise ValueError(f"Памылка пры загрузцы {json_path}: адсутнічае поле 'end' у адным з сегментаў")
            if part.start >= part.end:
                raise ValueError(
                    f"Памылка пры загрузцы {json_path}: start ({part.start}) мусіць быць меншы за end ({part.end})")
            if prev_end and part.start <= prev_end:
                raise ValueError(
                    f"Памылка пры загрузцы {json_path}: наступны start ({part.start}) мусіць быць большы за папярэдні end ({prev_end})")
            prev_end = part.end

        return obj
