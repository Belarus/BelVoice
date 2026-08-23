from belvoice.asr.SplitData import VoiceFile, VoicePart


class Merge2:
    """
    Усе інтэрвалы збіраем у 2 часткі, раздзеленыя па найбольшай паўзе,
    якая не бліжэй за 10% і не бліжэй за 30 секунд да пачатка і канца.

    Патрэбна для перанарэзкі аднаго сегмента калі LLM няправільна робіць ASR.
    """

    def __init__(self,
                 # мінімальная паўза
                 min_pause: float = 0.200,
                 # мінімальная адлегласць ад мяжы
                 min_length_percent: float = 10,
                 # мінімальная адлегласць ад мяжы
                 min_length_seconds: float = 30
                 ):
        self.min_pause = min_pause
        self.min_length_percent = min_length_percent
        self.min_length_seconds = min_length_seconds

    def merge(self, data: VoiceFile) -> None:
        n = len(data.segments)
        if n <= 2:
            return  # няма чаго дзяліць

        total_start = data.segments[0].start
        total_end = data.segments[-1].end
        total_duration = total_end - total_start

        # мінімальная дазволеная адлегласць ад пачатку/канца файла для кропкі разрэзу
        min_dist = max(total_duration * self.min_length_percent / 100.0, self.min_length_seconds)

        best_split_index = -1
        max_pause = -1.0

        for i in range(n - 1):
            pause = data.segments[i + 1].start - data.segments[i].end
            if pause < self.min_pause:
                continue

            # кропка разрэзу — сярэдзіна паўзы
            cut_point = (data.segments[i].end + data.segments[i + 1].start) / 2.0

            if cut_point - total_start < min_dist or total_end - cut_point < min_dist:
                continue  # занадта блізка да пачатку ці канца

            if pause > max_pause:
                max_pause = pause
                best_split_index = i

        if best_split_index == -1:
            # не знайшлі прыдатнай паўзы — не дзелім, аб'ядноўваем усё ў адзін сегмент
            data.segments = [VoicePart(start=total_start, end=total_end)]
            return

        # Дзелім на 2 часткі, захоўваючы дакладныя межы маўлення зыходных сегментаў
        part1 = VoicePart(start=total_start, end=data.segments[best_split_index].end)
        part2 = VoicePart(start=data.segments[best_split_index + 1].start, end=total_end)

        data.segments = [part1, part2]
