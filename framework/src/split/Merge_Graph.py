import networkx as nx
from .SplitData import VoiceFile, VoicePart


class Merge_Graph:
    """
    Разглядаем сегменты як граф, дзе рэбры паміж вузламі існуюць, калі адлегласць
    паміж імі менш за max_segment_duration.

    Аптымальныя межы кавалакаў для ацэнкі працягласці разлічваюцца па сярэдзіне паўз,
    але выніковыя сегменты захоўваюць дакладныя межы маўлення зыходных сегментаў.
    """

    FIXED_ASR_COST = 1000  # Умоўны штраф за адзін лішні выніковы сегмент
    MIN_EDGE_WEIGHT = 1.0  # Мінімальная вага рабра

    def __init__(self,
                 max_segment_duration: float = 10 * 60
                 ):
        self.max_segment_duration = max_segment_duration

    def _get_cut_point(self, idx: int, data: VoiceFile, n: int) -> float:
        """
        Вызначае віртуальную кропку разрэзу пасля сегмента з індэксам idx для ацэнкі даўжыні.
        idx = -1 адпавядае пачатку файла (0.0).
        idx = n - 1 адпавядае канцу апошняга сегмента.
        Для астатніх — гэта сярэдзіна паўзы паміж сегментамі idx і idx + 1.
        """
        if idx == -1:
            return 0.0
        if idx == n - 1:
            return data.segments[n - 1].end

        current_end = data.segments[idx].end
        next_start = data.segments[idx + 1].start
        return (current_end + next_start) / 2.0

    def merge(self, data: VoiceFile) -> None:
        if not data.segments:
            return

        G = nx.DiGraph()
        n = len(data.segments)

        # 1. Будуем рэбры графу (вылічэнне працягласці па сярэдзіне паўз)
        for i in range(-1, n - 1):
            start_time = self._get_cut_point(i, data, n)

            for j in range(i + 1, n):
                end_time = self._get_cut_point(j, data, n)
                duration = end_time - start_time

                # Абмяжоўваем даўжыню, захоўваючы сувязнасць графу
                if duration > self.max_segment_duration and j > i + 1:
                    break

                # Паўза пасля сегмента j для функцыі штрафу
                pause_after = 0.0
                if j + 1 < n:
                    pause_after = data.segments[j + 1].start - data.segments[j].end

                # Функцыя кошту рабра
                edge_weight = self.FIXED_ASR_COST - (pause_after * 50) + (self.max_segment_duration - duration)

                G.add_edge(i, j, weight=max(self.MIN_EDGE_WEIGHT, edge_weight))

        # 2. Пошук найкарацейшага шляху
        try:
            path = nx.shortest_path(G, source=-1, target=n - 1, weight='weight')
        except nx.NetworkXNoPath:
            path = list(range(-1, n))

        # 3. Пераводзім шлях у выніковыя інтэрвалы (па дакладных межах зыходных сегментаў)
        result_segments: list[VoicePart] = []
        for k in range(len(path) - 1):
            idx_start = path[k] + 1  # Індэкс першага сегмента ў аб'яднаным кавалку
            idx_end = path[k + 1]  # Індэкс апошняга сегмента ў аб'яднаным кавалку

            result_segments.append(
                VoicePart(start=data.segments[idx_start].start, end=data.segments[idx_end].end)
            )

        data.segments = result_segments
