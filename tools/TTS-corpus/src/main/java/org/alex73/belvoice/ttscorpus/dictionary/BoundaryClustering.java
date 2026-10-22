package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.fanetyka.impl.str.TokenStr;

/**
 * Кластэрызацыя па літарах і гуках (токенах) на сутыку двух слоў,
 * а таксама выдзяленне пачатку і канца слова (head/tail).
 */
public final class BoundaryClustering {
    private static final String VOWELS = "аоуэіыеёюя";
    private static final char STRESS = '\u0301';

    private BoundaryClustering() {
    }

    /**
     * Вяртае пачатак слова (head). Калі consonantsOnly == false, то ад пачатку да першай галоснай
     * (уключаючы галосную і націск). Калі consonantsOnly == true, то толькі зычныя перад першай
     * галоснай (без націскаў).
     */
    public static String head(String word, boolean consonantsOnly) {
        for (int i = 0; i < word.length(); i++) {
            if (VOWELS.indexOf(word.charAt(i)) >= 0) {
                if (consonantsOnly) {
                    return word.substring(0, i).replace(String.valueOf(STRESS), "");
                } else {
                    int end = i + 1;
                    if (end < word.length() && word.charAt(end) == STRESS) {
                        end++;
                    }
                    return word.substring(0, end);
                }
            }
        }
        return consonantsOnly ? word.replace(String.valueOf(STRESS), "") : word;
    }

    /**
     * Вяртае канец слова (tail). Калі consonantsOnly == false, то ад апошняй галоснай да канца
     * (уключаючы галосную). Калі consonantsOnly == true, то толькі зычныя пасля апошняй
     * галоснай (без націскаў).
     */
    public static String tail(String word, boolean consonantsOnly) {
        for (int i = word.length() - 1; i >= 0; i--) {
            if (VOWELS.indexOf(word.charAt(i)) >= 0) {
                if (consonantsOnly) {
                    int start = i + 1;
                    if (start < word.length() && word.charAt(start) == STRESS) {
                        start++;
                    }
                    return word.substring(start).replace(String.valueOf(STRESS), "");
                } else {
                    return word.substring(i);
                }
            }
        }
        return consonantsOnly ? word.replace(String.valueOf(STRESS), "") : word;
    }

    /**
     * Вяртае камбінацыю зычных літар на сутыку двух слоў (паміж апошняй галоснай 1-га слова
     * і першай галоснай 2-га слова, без саміх галосных) з прагалам паміж словамі.
     */
    public static String letterBoundary(String word1, String word2) {
        return tail(word1, true) + " " + head(word2, true);
    }

    /**
     * Вяртае камбінацыю токенаў (гукаў) на сутыку двух слоў (паміж апошнім галосным токенам 1-га слова
     * і першым галосным токенам 2-га слова) з прагалам паміж словамі.
     */
    public static String tokenBoundary(String transcription) {
        byte[] tokens = TokenStr.str2tokens(transcription);
        return tokenBoundary(tokens);
    }

    /**
     * Вяртае камбінацыю токенаў (гукаў) на сутыку двух слоў з масіва токенаў.
     */
    public static String tokenBoundary(byte[] tokens) {
        int spaceIdx = -1;
        for (int i = 0; i < tokens.length; i++) {
            if (tokens[i] == 0) { // Токен 0 адпавядае прагалу
                spaceIdx = i;
                break;
            }
        }

        if (spaceIdx < 0) {
            // Калі прагалу няма
            return null;
        }

        // Слова 1: шукаем апошні галосны перад прагалам
        int wFrom = spaceIdx;
        for (int i = spaceIdx - 1; i >= 0; i--) {
            if (!TokenStr.isVowel(tokens[i])) {
                wFrom = i;
            } else {
                break;
            }
        }
        // Слова 2: шукаем першы галосны пасля прагалу
        int wTo = spaceIdx;
        for (int i = spaceIdx + 1; i < tokens.length; i++) {
            if (!TokenStr.isVowel(tokens[i])) {
                wTo = i;
            } else {
                break;
            }
        }

        return TokenStr.tokens2str(tokens, wFrom, wTo + 1);
    }
}
