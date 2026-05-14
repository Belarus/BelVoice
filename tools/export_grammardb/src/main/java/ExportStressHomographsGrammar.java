import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.SetUtils;
import org.alex73.grammardb.StressUtils;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.structures.Paradigm;
import org.alex73.grammardb.structures.Variant;
import org.alex73.grammardb.tags.BelarusianTags;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.stream.Collectors;

void main() throws Exception {
    // unstressed -> stressed -> data[]
    Map<String, Map<String, List<Info>>> stressMap = new HashMap<>();
    Path dbOutput = Path.of("../../framework/src/stress/stresses-grammar.json");
    Gson gson = new GsonBuilder().disableHtmlEscaping().create();

    GrammarDB2 db = GrammarDB2.initializeFromJar();
    for (Paradigm p : db.getAllParadigms()) {
        for (Variant v : p.getVariant()) {
            for (Form f : v.getForm()) {
                String stressed = f.getValue();
                String unstressed = StressUtils.unstress(stressed);
                if (stressed.equals(unstressed)) {
                    continue;
                }
                Map<String, List<Info>> map = stressMap.computeIfAbsent(unstressed, k -> new TreeMap<>());
                List<Info> data = map.computeIfAbsent(stressed, k -> new ArrayList<>());
                data.add(new Info(p, v, f, new ArrayList<>()));
            }
        }
    }

    // адкідаем тыя, што не маюць амографаў
    for (Map.Entry<String, Map<String, List<Info>>> entry : stressMap.entrySet().stream().toList()) {
        if (entry.getValue().size() < 2) {
            stressMap.remove(entry.getKey());
        }
    }

    // запісваем граматычныя характарыстыкі
    BelarusianTags allTags = new BelarusianTags();
    stressMap.values().stream().flatMap(v -> v.values().stream()).flatMap(list -> list.stream()).forEach(in -> {
        String tag = SetUtils.tag(in.p, in.v, in.f);
        in.descList.add("Пачатковая форма слова - '" + StressUtils.unstress(in.v.getLemma()) + "'");
        in.descList.addAll(allTags.describe(tag, Set.of("Скланенне")));
    });

    Map<String, ResultInfo> resultMap = new TreeMap<>();
    StringBuilder txt = new StringBuilder();

    // абыходзім спачатку словы па частотнасці каб перагледзіць вачыма найбольш частотныя
    try (var in = this.getClass().getResourceAsStream("/frequent.txt");
         var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
        String word;
        while ((word = reader.readLine()) != null) {
            if (stressMap.containsKey(word)) {
                outputWord(word, stressMap, txt, resultMap);
                stressMap.remove(word);
            }
        }
    }
    txt.append("---------------------------\n");

    // абыходзім усе астатнія словы
    for (String unstressed : stressMap.keySet()) {
        outputWord(unstressed, stressMap, txt, resultMap);
    }
    Files.writeString(dbOutput, gson.toJson(resultMap));
    Files.writeString(Path.of("dump-grammars.txt"), txt);
    IO.println(stressMap.size());
}

void outputWord(String w, Map<String, Map<String, List<Info>>> stressMap, StringBuilder txt, Map<String, ResultInfo> resultMap) {
    txt.append("\n====== " + w + " ======\n");
    char vt = 'A';
    for (String stressed : stressMap.get(w).keySet()) {
        txt.append(vt + ": " + stressed.replace('\u0301', '+') + "  ");
        vt++;
    }
    txt.append("\n");
    String text = "";
    Map<Character, String> stressByVariant = new TreeMap<>();
    char v = 'A';
    for (Map.Entry<String, List<Info>> stressed : stressMap.get(w).entrySet()) {
        stressByVariant.put(v, stressed.getKey());
        text += "\nВарыянт " + v + ", калі слова мае адзін з набораў граматычных характарыстык:\n";
        text += stressed.getValue().stream().map(info -> "- " + String.join(", ", info.descList) + "\n").distinct().collect(Collectors.joining());
        v++;
    }
    txt.append(text);
    resultMap.put(w, new ResultInfo(stressByVariant, text));
}

record Info(Paradigm p, Variant v, Form f, List<String> descList) {
}

record ResultInfo(Map<Character, String> stressByVariant, String promptText) {
}


// праверыць:Дунай, чадзіце
