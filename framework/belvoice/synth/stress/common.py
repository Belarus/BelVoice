WORD_PATTERN = r'[ёйцукенгшўзхфывапролджэячсмітьбю\-\u02BC\u0301]+'


def word_match_case(original: str, result: str) -> str:
    """
    Калі зыходнае слова пачынаецца з вялікай літары, а вынік - з малой,
    робіць першую літару выніку вялікай (астатнія літары не мяняюцца).
    """
    if original[:1].isupper() and result[:1].islower():
        return result[0].upper() + result[1:]
    return result
