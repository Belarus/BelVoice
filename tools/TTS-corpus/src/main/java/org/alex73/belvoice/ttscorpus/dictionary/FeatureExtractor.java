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
 * Вымае фанетычныя прыкметы (diphone, triphone, phonetic rules) з фанетычнай транскрыпцыі.
 *
 * TODO: перарабіць вызначэнне фанетычных правілаў з BelG2P
 */
public final class FeatureExtractor {
    private FeatureExtractor() {
    }

    /**
     * Extracts all features (diphones, triphones, phonetic rules) from a phonetic result into WordData.
     */
    public static void fillFeatures(WordData data, G2PService.PhoneticResult r) {
        byte[] tokens= TokenStr.str2tokens(r.transcription());
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
