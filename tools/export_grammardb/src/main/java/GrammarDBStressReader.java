import org.alex73.grammardb.FormsReadyFilter;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.StressUtils;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.structures.Paradigm;
import org.alex73.grammardb.structures.Variant;

import java.util.*;

/**
 * Чытае ўсе формы з граматычнай базы, і дзеліць іх у залежнасці ад аманіміі націскаў:
 * <p>
 * 1. Правярае аманімію націскаў як для spell checker.
 * 2. Правярае аманімію націскаў як для паказу.
 * 3. Калі аманімія засталася - у спіс амонімаў.
 */
public class GrammarDBStressReader {
    // unstressed -> stressed ->  pdgVarId-> Info
    private final Map<String, Map<String, Map<String, Info>>> stressMapSpellChecker = new HashMap<>();
    private final Map<String, Map<String, Map<String, Info>>> stressMapShow = new HashMap<>();
    private final Map<String, Map<String, Map<String, Info>>> stressMapAll = new HashMap<>();
    public final GrammarDB2 db;

    public GrammarDBStressReader(String dir) throws Exception {
        db = GrammarDB2.initializeFromDir(dir);
        for (Paradigm p : db.getAllParadigms()) {
            for (Variant v : p.getVariant()) {
                add(stressMapSpellChecker, p, v, FormsReadyFilter.getAcceptedForms(FormsReadyFilter.MODE.SPELL, p, v));
                add(stressMapShow, p, v, FormsReadyFilter.getAcceptedForms(FormsReadyFilter.MODE.SHOW, p, v));
                add(stressMapAll, p, v, v.getForm());
            }
        }
    }

    private void add(Map<String, Map<String, Map<String, Info>>> stressMap, Paradigm p, Variant v, List<Form> forms) {
        if (forms == null) {
            return;
        }
        for (Form f : forms) {
            if (!StressUtils.hasStress(f.getValue())) {
                continue; // прапускаем без націска
            }
            String unstressed = StressUtils.unstress(f.getValue());
            String stressed = f.getValue();
            Map<String, Map<String, Info>> map = stressMap.computeIfAbsent(unstressed, k -> new TreeMap<>());
            Map<String, Info> stressedMap = map.computeIfAbsent(stressed, k -> new TreeMap<>());
            stressedMap.computeIfAbsent(p.getPdgId() + v.getId(), k -> new Info(p, v, new ArrayList<>())).f.add(f);
        }
    }

    // бяром толькі тыя, дзе толькі адзін варыянт націску
    public Map<String, String> getNoHomographs() {
        Map<String, String> singleStressMap = new HashMap<>();
        for (String noStressWord : stressMapAll.keySet()) {
            Map<String, Map<String, Info>> homographs = getHomographs(noStressWord);
            if (homographs.size() == 1) {
                singleStressMap.put(noStressWord, homographs.keySet().iterator().next());
            }
        }
        return singleStressMap;
    }

    // бяром толькі тыя, дзе больш за адзін варыянт націску
    public Map<String, Map<String, Map<String, Info>>> getHomographs() {
        Map<String, Map<String, Map<String, Info>>> homographsMap = new HashMap<>();
        for (String noStressWord : stressMapAll.keySet()) {
            Map<String, Map<String, Info>> homographs = getHomographs(noStressWord);
            if (homographs.size() > 1) {
                homographsMap.put(noStressWord, homographs);
            }
        }
        return homographsMap;
    }

    // вяртае мноства варыянтаў з націскам для слова без націску,
    // выкарыстоўваючы найбольш прыярытэтную мапу з наяўных
    private Map<String, Map<String, Info>> getHomographs(String noStressWord) {
        Map<String, Map<String, Info>> result = stressMapSpellChecker.get(noStressWord);
        if (result == null) {
            result = stressMapShow.get(noStressWord);
        }
        if (result == null) {
            result = stressMapAll.get(noStressWord);
        }
        return result;
    }


    record Info(Paradigm p, Variant v, List<Form> f) {
    }
}
