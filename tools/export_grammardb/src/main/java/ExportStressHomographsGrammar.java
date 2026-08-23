import org.alex73.grammardb.SetUtils;
import org.alex73.grammardb.StressUtils;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.tags.BelarusianTags;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Чытае граматычную базу і тлумачальны слоўнік каб экспартаваць граматыку і тлумачэнні
 * для зняцця аманіміі націскаў праз StressLLM.py.
 */
public class ExportStressHomographsGrammar {
    static Map<String, List<String>> tlumArticles;
    static int novalues = 0;
    static BufferedWriter bwShort, bwFull;
    static BelarusianTags allTags = new BelarusianTags();
    static Map<String, Filter> filtersToTlum = new HashMap<>();
    static Map<String, String> filtersDefinitions = new HashMap<>();


    void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("Памылка: не пазначаны шлях да файла.");
            System.err.println("Выкарыстанне: java ExportStressHomographsGrammar <шлях_да_файла_тлумачальнага>");
            System.exit(1);
        }
        // unstressed -> stressed ->  pdgVarId-> Info
        tlumArticles = new ParseTlum().getArticles(args[0]);
        readFilters();

        GrammarDBStressReader dbReader = new GrammarDBStressReader("/home/alex/gits/GrammarDB/data");
        Map<String, Map<String, Map<String, GrammarDBStressReader.Info>>> stressMap = dbReader.getHomographs();

        // запісваем граматычныя характарыстыкі
//        stressMap.values().stream().flatMap(v -> v.values().stream()).flatMap(list -> list.stream()).forEach(in -> {
//            String tag = SetUtils.tag(in.p, in.v, in.f);
//            in.descList.add("Пачатковая форма слова - '" + StressUtils.unstress(in.v.getLemma()) + "'");
//            in.descList.addAll(allTags.describe(tag, Set.of("Скланенне")));
//        });

        bwShort = Files.newBufferedWriter(Path.of("../../framework/belvoice/synth/stress/stresses-grammar_short.md"));
        bwFull = Files.newBufferedWriter(Path.of("../../framework/belvoice/synth/stress/stresses-grammar.md"));
        // абыходзім спачатку словы па частотнасці каб перагледзіць вачыма найбольш частотныя
        try (var in = this.getClass().getResourceAsStream("/frequent.txt");
             var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String word;
            while ((word = reader.readLine()) != null) {
                if (stressMap.containsKey(word)) {
                    outputWord(word, stressMap.get(word));
                    stressMap.remove(word);
                }
            }
        }

        // абыходзім усе астатнія словы
        for (Map.Entry<String, Map<String, Map<String, GrammarDBStressReader.Info>>> entry : stressMap.entrySet()) {
            // TODO   outputWord(entry.getKey(), entry.getValue());
        }

        bwShort.close();
        bwFull.close();

        IO.println("Агулам амонімаў: " + stressMap.size());
        IO.println("Слоў без значэнняў з тлумачальнага: " + novalues);
    }

    void readFilters() throws Exception {
        Pattern RE_DEF = Pattern.compile("([0-9]+[a-f])=>(.+)");
        Pattern RE_TO_TLUM = Pattern.compile("([0-9]+[a-f])=(.+?):(.+)");
        try (InputStream is = ParseTlum.class.getClassLoader().getResourceAsStream("filters.txt")) {
            if (is == null) {
                throw new Exception("Файл не знойдзены ў рэсурсах: filters.txt");
            }
            BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.replaceAll("#.+", "").trim();
                if (line.isEmpty()) continue;
                Matcher m;
                if ((m = RE_DEF.matcher(line)).matches()) {
                    if (filtersDefinitions.put(m.group(1), m.group(2)) != null) {
                        throw new Exception("Дубляванне ключа ў filters.txt: " + m.group(1));
                    }
                } else if ((m = RE_TO_TLUM.matcher(line)).matches()) {
                    if (filtersToTlum.put(m.group(1), new Filter(m.group(1), m.group(2).replace('+', '\u0301'), m.group(3))) != null) {
                        throw new Exception("Дубляванне ключа ў filters.txt: " + m.group(1));
                    }
                } else {
                    throw new Exception("Няправільны фармат у filters.txt: " + line);
                }
            }
        }
    }

    /**
     * Вывад інфармацыі пра адно слова.
     */
    void outputWord(String w, Map<String, Map<String, GrammarDBStressReader.Info>> stressMap) throws Exception {
        String textShort = "";
        String textFull = "";
        String header = "";
        Map<String, Integer> tlumCounts = new TreeMap<>();

        // праверыць - ці ва ўсіх значэннях выкарыстоўваецца адна і тая ж парадыгма
        boolean theSameParadigm = stressMap.values().stream().flatMap(v -> v.values().stream())
                .map(in -> in.p().getPdgId() + in.v().getId())
                .distinct().count() == 1;

        char v = 'A';
        for (Map.Entry<String, Map<String, GrammarDBStressReader.Info>> stressed : stressMap.entrySet()) {
            if (v != 'A') {
                header += "; ";
            }
            header += v + ": " + stressed.getKey();
            textShort += "\n\n## Variant " + v + " " + stressed.getKey() + "\n\n"; // TODO
            textFull += "\n\n## Variant " + v + "\n\n";
            for (GrammarDBStressReader.Info in : stressed.getValue().values()) {
                String lemmaGrammar = String.join(", ", allTags.describe(SetUtils.tag(in.p(), in.v()), Set.of("Скланенне")));
                textShort += "\n### Пачатковая форма слова — '" + StressUtils.unstress(in.v().getLemma()) + "', слова мае граматычныя характарыстыкі: " + lemmaGrammar + " {" + in.p().getPdgId() + in.v().getId() + "}\n";
                textFull += "\n### Пачатковая форма слова — '" + StressUtils.unstress(in.v().getLemma()) + "', слова мае граматычныя характарыстыкі: " + lemmaGrammar + "\n";

                String textForms = "";
                for (Form f : in.f()) {
                    String formGrammar = String.join(", ", allTags.describe(SetUtils.tag(in.p(), in.v(), f), Set.of("Скланенне")));
                    if (!formGrammar.startsWith(lemmaGrammar)) {
                        throw new Exception("Памылка ў граматыцы");
                    }
                    formGrammar = formGrammar.substring(lemmaGrammar.length());
                    if (!formGrammar.isEmpty()) {
                        textForms += "- " + formGrammar.substring(2) + "\n";
                    }
                }
                if (!textForms.isEmpty()) {
                    textShort += "\nСлова мае адну з граматычных характарыстык формы:\n" + textForms;
                    textFull += "\nСлова мае адну з граматычных характарыстык формы:\n" + textForms;
                }

                String pdgVarId = in.p().getPdgId() + in.v().getId();
                if (theSameParadigm) {
                    // прапускаем значэнне з тлумачальнага, бо ў варыянтах адна і тая ж парадыгма
                } else if (filtersToTlum.containsKey(pdgVarId)) {
                    // спасылка вызначана ў filters.txt
                    Filter filter = filtersToTlum.get(pdgVarId);
                    String tlumKey = filter.key;
                    List<String> tlumDefs = new ArrayList<>();
                    for (String def : tlumArticles.get(tlumKey)) {
                        if (def.startsWith(filter.defStart)) {
                            tlumDefs.add(def);
                        }
                    }
                    switch (tlumDefs.size()) {
                        case 1:
                            break;
                        case 0:
                        default:
                            throw new Exception();
                    }
                    textShort += "\n### Слова '" + tlumKey + "' мае значэнні: " + tlumDefs.get(0).substring(0, Math.min(200, tlumDefs.get(0).length())).replace("\n", " ") + "\n";
                    textFull += "\n### Слова '" + tlumKey + "' мае значэнні: " + tlumDefs.get(0) + "\n";
                } else if (filtersDefinitions.containsKey(pdgVarId)) {
                    textShort += "\n### Слова мае значэнні: " + filtersDefinitions.get(pdgVarId) + "\n";
                    textFull += "\n### Слова мае значэнні: " + filtersDefinitions.get(pdgVarId) + "\n";
                } else {
                    // шукаем у тлумачальным
                    String tlumKey;
                    List<String> tlumDefs = tlumArticles.get(tlumKey = in.v().getLemma());
                    if (tlumDefs == null) {
                        tlumDefs = tlumArticles.get(tlumKey = StressUtils.setUsuallyStress(in.v().getLemma()));
                    }
                    if (tlumDefs == null) {
                        tlumDefs = tlumArticles.get(tlumKey = StressUtils.unstress(in.v().getLemma()));
                    }
                    if (tlumDefs == null) {
                        textShort += "\n### ??? няма значэнняў з тлумачальнага\n";
                        textFull += "\n### ??? няма значэнняў з тлумачальнага\n";
                        novalues++;
                    } else {
                        for (String def : tlumDefs) {
                            textShort += "\n### Слова '" + tlumKey + "' мае значэнні: " + def.substring(0, Math.min(200, def.length())).replace("\n", " ") + "\n";
                            textFull += "\n### Слова '" + tlumKey + "' мае значэнні: " + def + "\n";
                            tlumCounts.put(tlumKey, tlumCounts.getOrDefault(tlumKey, 0) + 1);
                        }
                    }
                }
            }
            v++;
        }

        for (Map.Entry<String, Integer> entry : tlumCounts.entrySet()) {
            if (entry.getValue() > 1) {
                textShort += "\n### ??? дублюецца значэнне тлумачальнага: " + entry.getKey() + "\n";
                textFull += "\n### ??? дублюецца значэнне тлумачальнага: " + entry.getKey() + "\n";
            }
        }

        textShort = "\n\n# " + header + "\n\n" + textShort.replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n");
        textFull = "\n\n# " + header + "\n\n" + textFull.replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n");
        bwShort.write(textShort);
        bwFull.write(textFull);
    }

    record Filter(String pdgVarId, String key, String defStart) {
    }

// праверыць:Дунай, чадзіце
}
