import litellm
import os
import json

import re
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../framework/src')))
from belvoice.synth.stress import StressLLM
from belvoice.synth.stress import StressStat

word_pattern = r'([ёйцукенгшўзхфывапролджэячсмітьбю\u02BC\u0301\+]+)'

litellm.num_retries = 3


class Benchmark:
    known_answers = {}
    ok_count = 0
    total_count = 0
    ok_per_word = {}
    total_per_word = {}
    errors_per_word = {}

    def __init__(self, input_file: str, out_file_prefix: str):
        self._input_file = input_file
        self._out_file_prefix = out_file_prefix

        # чытаем папярэднія вынікі
        if os.path.exists(out_file_prefix + ".jsonl"):
            with (open(out_file_prefix + ".jsonl", "rt") as in_f):
                for line in in_f:
                    record = json.loads(line)
                    self.known_answers[record["text"]] = record["result"]

    def inc_per_word(self, word: str, ok: bool, text: str):
        if word not in self.total_per_word:
            self.total_per_word[word] = 0
            self.ok_per_word[word] = 0

        self.total_per_word[word] += 1
        self.total_count += 1
        if ok:
            self.ok_per_word[word] += 1
            self.ok_count += 1
        else:
            if not word in self.errors_per_word:
                self.errors_per_word[word] = []
            self.errors_per_word[word].append(text)

    def process(self):
        with open(self._out_file_prefix + ".jsonl", "at", buffering=4096) as out_f:
            # чытаем звесткі для benchmark
            with open(self._input_file, "r") as f:
                for line in f:
                    parts = re.split(word_pattern, line, flags=re.IGNORECASE)

                    for i, part in enumerate(parts):
                        if not re.fullmatch(word_pattern, part, flags=re.IGNORECASE) or not '+' in part:
                            # гэта не слова, альбо слова без пазначанага націску
                            continue

                        part_unstressed = part.replace("+", "")
                        part_unstressed_lower = part_unstressed.lower()

                        text_stresses = "".join(parts[:i]) + f"[{part}]" + "".join(parts[i + 1:])
                        text = text_stresses.replace("\u0301", "+").replace("+", "")

                        if part_unstressed in self.engine._stresses_nohomographs:
                            word = self.engine._stresses_nohomographs[part_unstressed].replace("\u0301", "+")
                            if word != part:
                                raise Exception(
                                    f"Слова з націскам у тэксце не супадае з адзіным варыянтам націску ('{word}'): {text_stresses}")
                        else:
                            if text in self.known_answers:
                                word = self.known_answers[text]
                                self.inc_per_word(part_unstressed_lower, word.lower() == part.lower(), text)
                            else:
                                word, response = self.check_word(part_unstressed, text)
                                if not word:
                                    # невядомае слова
                                    continue
                                word = word.replace("\u0301", "+")
                                record = json.dumps({
                                    "word_expected": part,
                                    "result": word,
                                    "response": response.model_dump() if response else None,
                                    "text": text},
                                    ensure_ascii=False)
                                out_f.write(record + "\n")
                                self.inc_per_word(part_unstressed_lower, word.lower() == part.lower(), text)

        for w in self.total_per_word:
            if self.total_per_word[w] > 0:
                print(
                    f"Націскі для {w}: {self.ok_per_word[w]}/{self.total_per_word[w]} = {self.ok_per_word[w] / self.total_per_word[w] * 100:.2f}%")
            else:
                print(f"Націскі для {w}: {self.ok_per_word[w]}/{self.total_per_word[w]}")
        print(f"Агулам: {self.ok_count}/{self.total_count} = {self.ok_count / self.total_count * 100:.2f}%")

    def show_errors(self):
        for w in self.errors_per_word:
            for text in self.errors_per_word[w]:
                print(f"{w}: {text.strip()}")


class BenchmarkLLM(Benchmark):
    def __init__(self, input_file: str, out_file_prefix: str, model: str):
        Benchmark.__init__(self, input_file, out_file_prefix)
        self.engine = StressLLM(model)

    def check_word(self, word: str, full_text: str) -> (str, dict):
        if self.total_count == 0:
            print(f"{self.total_count} - {word}")
        else:
            print(f"{self.total_count} - {word}      {self.ok_count / self.total_count * 100:.2f}%")
        return self.engine.request_llm(word.lower(), full_text)  # TODO lower


class BenchmarkStat(Benchmark):
    def __init__(self, input_file: str, out_file_prefix: str):
        Benchmark.__init__(self, input_file, out_file_prefix)
        self.engine = StressStat()

    def check_word(self, word: str, full_text: str) -> (str, dict):
        return (self.engine.process_word(word), None)

# BenchmarkLLM("data/common_voice.txt", "common-gemma4-26-nothink", "openrouter/google/gemma-4-26b-a4b-it").process()
# BenchmarkLLM("data/zascienak_Malinauka.txt", "malinauka-gemma4-26-nothink",
#             "openrouter/google/gemma-4-26b-a4b-it").process()

# BenchmarkLLM("data/common_voice.txt", "common-gemini31fl-nothink", "openrouter/google/gemini-3.1-flash-lite").process()
# p = BenchmarkLLM("data/zascienak_Malinauka.txt", "malinauka-gemini31fl-nothink",
#                 "openrouter/google/gemini-3.1-flash-lite")
# p.process()
# p.show_errors()

# BenchmarkStat("data/common_voice.txt", "common_stat").process()
BenchmarkStat("data/zascienak_Malinauka.txt", "malinauka_stat").process()
