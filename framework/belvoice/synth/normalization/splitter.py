import stanza
from stanza.pipeline.core import DownloadMethod
from stanza.models.common.doc import Sentence


class SentenceInfo:
    def __init__(self, splitter, sentence: Sentence):
        self._splitter = splitter
        self._sentence = sentence

    @property
    def text(self) -> str:
        """ Access the list of sentences for this document. """
        return self._sentence.text

    ALLOWED_CHARS = set("ёйцукенгшўзхфывапролджэячсмітьбюЁЙЦУКЕНГШЎЗХФЫВАПРОЛДЖЭЯЧСМІТЬБЮґ-'’")
    KNOWN_ISSUES = ["?!."]

    @property
    def is_normalized(self) -> bool:
        """ Ці нармалізаваны сказ - правяраем па словах """
        return not self.debug_notnormalized()

    def debug_notnormalized(self) -> str:
        for word in self._sentence.words:
            if word.upos == 'PUNCT' or word.upos == 'SYM':  # TODO : праверыць SYM
                continue  # пунктуацыю не правяраем
            if any(char not in self.ALLOWED_CHARS for char in word.text):
                if word.text not in self.KNOWN_ISSUES:
                    return word.text
        return None

    def normalize(self, normalization_function):
        normalized_text = normalization_function(self._sentence.text)
        self._sentence = self._splitter.parse_one_sentence(normalized_text)

    def convert_tts(self, conversion_function) -> str:
        """
        Канвертаванне спалучэнняў слоў, не падзеленых пунктуацыяй, ў IPA (ці іншы стандарт для TTS).
        Для беларускай мовы колькасць words і tokens у Sentence мусіць быць аднолькавая, і start_char і end_char у іх мусіць супадаць.
        Канвертаваць мае сэнс толькі тыя сказы, якія нармалізаваныя (is_normalized==True)
        """
        result = ""
        buffer = ""
        if len(self._sentence.tokens) != len(self._sentence.words):
            raise Exception("Колькасць tokens і words не супадае ў Sentence")
        for word, token in zip(self._sentence.words, self._sentence.tokens, strict=True):
            if word.start_char != token.start_char or word.end_char != token.end_char:
                raise Exception("Пазіцыі token і word не супадаюць ў Sentence")

            if word.upos == 'PUNCT' or word.upos == 'SYM':
                result += conversion_function(buffer)
                buffer = ""
                result += token.spaces_before + token.text + token.spaces_after
            else:
                buffer += token.spaces_before + token.text + token.spaces_after

        if buffer:
            result += conversion_function(buffer)
        return result

    def __repr__(self) -> str:
        return f"Sentence({self._sentence.text}, normalized={self.is_normalized()})"


class BelSplitter:
    # Перадавайце check_normalized=True калі вы збіраецеся правяраць словы на is_normalized.
    # Калі проста падзяліць на сказы - check_normalized=True будзе працаваць разы ў тры хутчэй
    def __init__(self, check_normalized: bool = True):
        if check_normalized:
            self._nlp = stanza.Pipeline('be', processors='tokenize,pos', download_method=DownloadMethod.REUSE_RESOURCES)
        else:
            self._nlp = stanza.Pipeline('be', processors='tokenize', download_method=DownloadMethod.REUSE_RESOURCES)

    # Splits text to separate sentences
    # text - array of paragraphs
    # result - paragraphs contains sentences
    def parse(self, paragraphs: list[str]) -> list[list[SentenceInfo]]:
        result_paragraphs = self._nlp.bulk_process(paragraphs)
        return [[SentenceInfo(self, s) for s in p.sentences] for p in result_paragraphs]

    def parse_one_sentence(self, text: str) -> Sentence:
        result_sentences = self._nlp(text)
        if len(result_sentences.sentences) != 1:
            raise Exception(f"Stanza returns multiple sentences after one sentence normalization: {text}")
        return result_sentences.sentences[0]
