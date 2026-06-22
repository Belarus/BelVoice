#
# Тут знаходзіцца код для разбіўкі аўдыяфайла на часткі, вызначэння спікераў, распазнавання маўлення.
# Гэта дазваляе распазнаваць маўленне з пазнакамі часу і спікераў, напрыклад, для субцітраў ці корпусу.
#
import json
import tempfile
import subprocess
from pathlib import Path


class VoicePart:
    """
    Утрымлівае інфармацыю пра адну частку аўдыяфайла (маўленне аднаго чалавека без паўзы).
    """

    def __init__(self,
                 start: float = None,  # пачатак маўленчага фрагмента ў секундах
                 end: float = None,  # канец маўленчага фрагмента ў секундах
                 speaker_id: str = None,  # хто гаворыць
                 text: str = None  # распазнаны тэкст
                 ) -> None:
        self.start = start
        self.end = end
        self.speaker_id = speaker_id
        self.text = text

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "speaker_id": getattr(self, "speaker_id", None),
            "text": getattr(self, "text", None)
        }

    @staticmethod
    def from_dict(data: dict) -> 'VoicePart':
        part = VoicePart()
        part.start = data.get("start")
        part.end = data.get("end")
        part.speaker_id = data.get("speaker_id")
        part.text = data.get("text", None)
        return part


class VoiceFile:
    """
    Утрымлівае інфармацыю пра ўсе часткі аўдыяфайла.
    """

    def __init__(self, audio_file_path: str | Path = None, audio_files_base: str | Path = None) -> None:
        self.audio_file_path = audio_file_path
        self.audio_files_base = audio_files_base
        self.segments: list[VoicePart] = []

    def to_string(self) -> str:
        data = {
            "audio_file_path": str(self.audio_file_path) if self.audio_file_path else None,
            "segments": [part.to_dict() for part in self.segments]
        }
        return json.dumps(data, ensure_ascii=False, indent=4)

    def save_to_json(self, json_path: str) -> None:
        data = {
            "audio_file_path": str(self.audio_file_path) if self.audio_file_path else None,
            "segments": [part.to_dict() for part in self.segments]
        }
        out = Path(json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        temp_file = out.with_suffix(".new")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        temp_file.replace(out)

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
    def dump_stats(files) -> None:  # :list[VoiceFile]
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
    def load_from_json(json_path: str, audio_files_base: str) -> 'VoiceFile':
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        obj = VoiceFile(data.get("audio_file_path"), audio_files_base)
        obj.segments = [VoicePart.from_dict(p) for p in data.get("segments", [])]

        prev_end = None
        for part in obj.segments:
            if part.start is None:
                raise ValueError(f"Памылка пры чытанні {json_path}: адсутнічае поле 'start' у адным з сегментаў")
            if part.end is None:
                raise ValueError(f"Памылка пры чытанні {json_path}: адсутнічае поле 'end' у адным з сегментаў")
            if part.start > part.end:
                raise ValueError(
                    f"Памылка пры чытанні {json_path}: start ({part.start}) мусіць быць меншы за end ({part.end})")
            if prev_end and part.start < prev_end - 0.1:  # дазваляе невялікае перакрыццё для кампенсацыі дробных памылак у таймстэмпах
                raise ValueError(
                    f"Памылка пры чытанні {json_path}: наступны start ({part.start}) мусіць быць большы за папярэдні end ({prev_end})")
            prev_end = part.end

        return obj

    def segment2wav(self, segment: VoicePart = None) -> str:
        return self.extract_wav(Path(self.audio_files_base) / self.audio_file_path,
                                segment.start if segment else None, segment.end if segment else None)

    @staticmethod
    def extract_wav(audio_file: str | Path, start=None, end=None, convert_to_format: str = "wav") -> str:
        """
        Extract part of audio file using ffmpeg with ASR-specific parameters: wav mono, 16k, pcm_s16le.
        """
        temp_file = tempfile.NamedTemporaryFile(suffix="." + convert_to_format, delete=False)
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(audio_file),
            "-ar", "16000",
            "-ac", "1"
        ]
        if convert_to_format == "wav":
            cmd.extend(["-acodec", "pcm_s16le"])
        if start is not None:
            cmd.extend(["-ss", str(start)])
        if end is not None:
            cmd.extend(["-to", str(end)])
        cmd.append(temp_file.name)

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return temp_file.name
