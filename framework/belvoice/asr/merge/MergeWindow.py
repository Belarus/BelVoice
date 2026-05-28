from belvoice.asr.SplitData import VoiceFile, VoicePart


class MergeWindow:
    """
    Шукаем максімальную паўзу(але не меншую за 200мс) ў нейкім вакне часу (8-10 хвілін), і рэжам па ёй.
    Калі паўзаў няма, рэжам па паўзе большай за 200мс, якая ёсць да 8 хвілін.
    """

    def __init__(self,
                 # мінімальная паўза
                 min_pause: float = 0.200,
                 # мінімальная працягласць кавалка, пасля якой пачынаем шукаць паўзы для разрэзу
                 min_segment_duration: float = 8 * 60,
                 # максімальная працягласць кавалка, да якой абавязкова рэжам па найбольшай паўзе
                 max_segment_duration: float = 10 * 60
                 ):
        self.min_pause = min_pause
        self.min_segment_duration = min_segment_duration
        self.max_segment_duration = max_segment_duration

    def merge(self, data: VoiceFile) -> None:
        result_segments: list[VoicePart] = []

        i = 0
        current_chunk_start = 0.0
        while i < len(data.segments):
            best_split_index = i
            max_pause = -1.0
            # Зменныя для рэзервовага разрэзу (да 8 хвілін)
            fallback_split_index = -1

            # Набіраем сегменты, пакуль не ўпрэмся ў максімальную мяжу
            j = i
            while j < len(data.segments):
                # Разлічваем паўзу ПАСЛЯ бягучага сегмента
                if j + 1 < len(data.segments):
                    pause = data.segments[j + 1].start - data.segments[j].end
                    current_chunk_end = data.segments[j].end + pause / 2.0
                else:
                    pause = 0
                    current_chunk_end = data.segments[j].end

                chunk_duration = current_chunk_end - current_chunk_start

                if chunk_duration > self.max_segment_duration:
                    break  # Перавысілі 10 хвілін

                # Калі мы ў "вакне пошуку" (напрыклад, 8 - 10 хвілін)
                if chunk_duration >= self.min_segment_duration:
                    # Ігнаруем паўзы меншыя за 200мс
                    if pause >= self.min_pause and pause > max_pause:
                        max_pause = pause
                        best_split_index = j
                else:
                    # Мы яшчэ да 8 хвілін, шукаем запасную паўзу (>200мс)
                    if pause >= self.min_pause:
                        fallback_split_index = j

                j += 1

            # Калі ў акне 8-10 хв не было ніводнай паўзы > 200мс
            if best_split_index == i and j > i:
                if j == len(data.segments):
                    # дайшлі да канца файла
                    best_split_index = j - 1
                elif fallback_split_index != -1:
                    # Рэжам па паўзе большай за 200мс, якая ёсць да 8 хвілін
                    best_split_index = fallback_split_index
                else:
                    # Экстрэмальны выпадак: да 10 хв увогуле няма ніводнай паўзы > 200мс.
                    # Рэжам проста па ліміце.
                    best_split_index = j - 1

            # Разлічваем канец для разрэзанага кавалка
            if best_split_index + 1 < len(data.segments):
                pause_after_split = data.segments[best_split_index + 1].start - data.segments[best_split_index].end
                chunk_end_time = data.segments[best_split_index].end + pause_after_split / 2.0
            else:
                chunk_end_time = data.segments[best_split_index].end

            # Збіраем фінальны кавалак
            chunk_segments = data.segments[i: best_split_index + 1]
            result_segments.append(VoicePart(start=chunk_segments[0].start, end=chunk_segments[-1].end))

            # Пераходзім да наступнага кавалка
            current_chunk_start = chunk_end_time
            i = best_split_index + 1

        data.segments = result_segments
