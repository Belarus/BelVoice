package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.belvoice.ttscorpus.model.WordData;
import org.alex73.fanetyka.impl.Huk;
import org.alex73.fanetyka.impl.str.TokenStr;
import org.alex73.fanetyka.impl.str.VoiceToStringTTS;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Вымае фанетычныя прыкметы (diphone, triphone, phonetic rules) з фанетычнай транскрыпцыі
 * і графіка-тэкставыя n-грамы (digraph, trigraph) з тэксту слоў.
 *
 * TODO: перарабіць вызначэнне фанетычных правілаў з BelG2P
 */
public final class FeatureExtractor {
    private FeatureExtractor() {
    }

    /**
     * Extracts all features (digraphs, trigraphs, diphones, triphones, phonetic rules) into WordData.
     */
    public static void fillFeatures(WordData data, G2PService.PhoneticResult r) {
        if (data.words() != null) {
            List<String> digraphs = textWindows(data.words(), 2);
            if (!digraphs.isEmpty()) {
                data.setDigraph(String.join(";", digraphs));
            }
            List<String> trigraphs = textWindows(data.words(), 3);
            if (!trigraphs.isEmpty()) {
                data.setTrigraph(String.join(";", trigraphs));
            }
        }
        byte[] tokens = TokenStr.str2tokens(r.transcription());
        data.setPhoneticTranscription(r.transcription());
        List<String> diphones = windows(tokens, 2);
        if (!diphones.isEmpty()) {
            data.setDiphone(String.join(";", diphones));
        }
        List<String> triphones = windows(tokens, 3);
        if (!triphones.isEmpty()) {
            data.setTriphone(String.join(";", triphones));
        }
        if (!r.rules().isEmpty()) {
            Set<String> rules = new LinkedHashSet<>(r.rules());
            data.setPhoneticRule(String.join(";", rules));
        }
    }

    /**
     * Выбірае n-грамы літар (дыграфы, трыграфы) з тэксту.
     * Прабелы і камбінаваныя знакі захоўваюцца ў выніковым радку, але не ўлічваюцца пры падліку.
     */
    static List<String> textWindows(String text, int n) {
        if (text == null || n <= 0) {
            return Collections.emptyList();
        }
        String lower = text.toLowerCase();
        List<String> result = new ArrayList<>();
        for (int i = 0; i < lower.length(); i++) {
            if (lower.charAt(i) == ' ' || lower.charAt(i)=='\u0301') { // combining acute accent
                continue;
            }
            int count = 0;
            int j = i;
            while (j < lower.length() && count < n) {
                char c = lower.charAt(j);
                if (c != ' ' && c != '\u0301') { // combining acute accent
                    count++;
                }
                j++;
            }
            if (count == n) {
                while (j < lower.length() && lower.charAt(j) == '\u0301') { // combining acute accent
                    j++;
                }
                result.add(lower.substring(i, j));
            }
        }
        return result;
    }

    /**
     * Выбірае n-грамы фанетычных токенаў.
     * Кожнае акно павінна змяшчаць роўна n значных токенаў (не роўных 0).
     * Токен 0 (прагал) прапускаецца пры падліку колькасці токенаў,
     * але захоўваецца ў выніковым радку, калі знаходзіцца паміж значнымі токенамі.
     */
    static List<String> windows(byte[] tokens, int n) {
        if (tokens == null || n <= 0) {
            return Collections.emptyList();
        }
        List<String> result = new ArrayList<>();
        // Перабіраем усе магчымыя пачатковыя пазіцыі для акна
        for (int i = 0; i < tokens.length; i++) {
            // Прапускаем прагал (токен 0): акно не можа пачынацца з прагала
            if (tokens[i] == 0) {
                continue;
            }

            int count = 0;
            int j = i;
            // Рухаемся наперад, пакуль не набяром роўна n значных токенаў
            while (j < tokens.length && count < n) {
                // Пры разліку колькасці токенаў прапускаем токен з значэннем 0 (прагал)
                if (tokens[j] != 0) {
                    count++;
                }
                j++;
            }

            // Калі ўдалося знайсці акно з n значных токенаў, дадаем яго ў вынік
            // (дыяпазон ад i да j уключае ўсе значныя токены і прагалы паміж імі)
            if (count == n) {
                result.add(TokenStr.tokens2str(tokens, i, j));
            }
        }
        return result;
    }
}
