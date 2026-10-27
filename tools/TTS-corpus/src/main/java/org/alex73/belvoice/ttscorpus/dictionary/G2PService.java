package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.fanetyka.impl.Fanetyka3;
import org.alex73.fanetyka.impl.FanetykaConfig;
import org.alex73.fanetyka.impl.Huk;
import org.alex73.fanetyka.impl.Logger;
import org.alex73.fanetyka.impl.str.VoiceToStringTTS;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Thread-safe wrapper over BelG2P: new Fanetyka3 is created for each call.
 */
public class G2PService {
    private static final Pattern RULE = Pattern
            .compile("<b>\\d+\\.</b> <b>([^<]+)</b>: \\[[^\\]]*\\]\\. ([^;<]*);");

    private static final VoiceToStringTTS HUK2STR = new VoiceToStringTTS();

    private final FanetykaConfig config;

    public G2PService(FanetykaConfig config) {
        this.config = config;
    }

    public PhoneticResult transcribe(List<String> words) throws Exception {
        Fanetyka3 f = new Fanetyka3(config);
        List<String> rules = new ArrayList<>();
        f.logPhenomenon = new Logger() {
            @Override
            public void logAttention(String msg) {
            }

            @Override
            public void logPrepare(String msg) {
            }

            @Override
            public void logChange(String msg) {
            }

            @Override
            public void logChange(String title, String details, String changeFrom, String changeTo, String dumpFrom, String dumpTo, String caseCode, List<Huk> hukiBefore) {
                rules.add(caseCode + ":" + HUK2STR.toString(hukiBefore));
            }
        };
        f.calcFanetyka(new ArrayList<>(words));
        String transcription = f.toString(HUK2STR);
        return new PhoneticResult(transcription, rules);
    }

    public record PhoneticResult(String transcription, List<String> rules) {
    }
}
