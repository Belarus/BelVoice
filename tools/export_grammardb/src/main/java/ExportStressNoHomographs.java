import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.StressUtils;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.structures.Paradigm;
import org.alex73.grammardb.structures.Variant;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

void main() throws Exception {
    Map<String, Set<String>> stressMap = new HashMap<>();
    Path dbOutput = Path.of("../../framework/src/stress/stresses-nohomonyms.json");
    Gson gson = new GsonBuilder().disableHtmlEscaping().create();

    GrammarDB2 db = GrammarDB2.initializeFromJar();
    for (Paradigm p : db.getAllParadigms()) {
        for (Variant v : p.getVariant()) {
            for (Form f : v.getForm()) {
                if (!StressUtils.hasStress(f.getValue())) {
                    continue; // прапускаем без націска
                }
                String unstressed = StressUtils.unstress(f.getValue());
                stressMap.computeIfAbsent(unstressed, k -> new TreeSet<>()).add(f.getValue());
            }
        }
    }

    // бяром толькі тыя, дзе толькі адзін варыянт націску
    Map<String, String> singleStressMap = stressMap.entrySet().stream()
            .filter(e -> e.getValue().size() == 1)
            .collect(Collectors.toMap(
                    Map.Entry::getKey,
                    e -> e.getValue().iterator().next()
            ));

    Files.writeString(dbOutput, gson.toJson(singleStressMap));
    IO.println("Successfully wrote " + singleStressMap.size() + " stress entries to " + dbOutput.toAbsolutePath());
}
