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

    @staticmethod
    def load_from_json(json_path: str) -> 'VoiceFile':
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        obj = VoiceFile(data.get("audio_file_path"))
        obj.segments = [VoicePart.from_dict(p) for p in data.get("segments", [])]
        return obj
