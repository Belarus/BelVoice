package org.alex73.fanetyka.impl.str;

import org.alex73.fanetyka.impl.Huk;

import java.util.List;
import java.util.Map;

/**
 * Гэты клас канвертуе гукі з BelG2P у фармат, які выкарыстоўваецца ў TTS.
 * <p>
 * Гэты фармат падобны на школьны варыянт запісу гукаў, але забяспечвае дакладнае аднаўленне гукаў з тэкставага зупісу.
 * <p>
 * За аснову ўзятыя літары беларускага алфівіту з некаторымі асаблівасцямі канвертавання каб мець адрозныя токены для розных гукаў:
 * - мяккія і цвёрдыя зычныя - пазначаюцца знакам мяккасці (напрыклад, [н] і [нʲ])
 * - націскныя і ненаціскныя галосныя - пазначаюцца знакам націску 0x00B4 (напрыклад, [а] і [а´])
 * - доўгія і кароткія зычныя - пазначаюцца знакам падваення (напрыклад, [н] і [нː])
 * - гукі 'дж' і 'дз' пазначаюцца як 'ž' і 'ž' адпаведна
 *
 * Ён працуе ў пары з TokenStr, які канвертуе гукі з тэкставага фармату ў int-токены і наадварот.
 */
public class VoiceToStringTTS extends ToStringBase {
    private static final Map<Huk.POUNY_HUK, String> MAP = loadOutputMap("out_belvoice.txt");

    @Override
    protected String huk2str(Huk huk) {
        return MAP.get(huk.pouny());
    }

    @Override
    protected char getStressCharBefore() {
        return 0;
    }

    @Override
    protected char getStressCharAfter() {
        return '\u00B4';
    }

    @Override
    protected char getPadvojenyChar() {
        return 'ː';
    }

    public String toString(List<Huk> huki) {
        StringBuilder out = new StringBuilder();
        String prevHukStr = null;
        for (Huk h : huki) {
            String hukStr = huk2str(h);
            if (!Huk.halosnyja.contains(h.bazavyHuk) && hukStr.equals(prevHukStr)) {
                // гук такі самы які папярэдні
                if (out.charAt(out.length() - 1) == ' ') {
                    // падваенне вакол прагала - прагала не мусіць быць наогул
                    out.setCharAt(out.length() - 1, getPadvojenyChar());
                } else {
                    out.append(getPadvojenyChar());
                }
            } else {
                out.append(hukStr);
            }
            prevHukStr = hukStr;
            if (getStressCharAfter() != 0 && h.stress) {
                out.append(getStressCharAfter());
            }
            if ((h.padzielPasla & (Huk.PADZIEL_SLOVY | Huk.PADZIEL_PRYNAZOUNIK)) != 0) {
                out.append(' ');
            }
        }

        // адкідаем прагал у канцы - нельга рабіць гэта пры канвертацыі слоў, бо тады не
        // будзе спрацоўваць праверка на канец слова
        return out.toString().trim();
    }
}
