import com.google.gson.Gson;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.StressUtils;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.structures.Paradigm;
import org.alex73.grammardb.structures.Variant;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

void main() throws Exception {
    Map<String, String> stressMap = new HashMap<>();
    Path dbOutput = Path.of("../../framework/binaries/stresses.json");
    Path dbStatOutput = Path.of("../../framework/binaries/stresses-stat.json");

    GrammarDB2 db = GrammarDB2.initializeFromJar();
    for (Paradigm p : db.getAllParadigms()) {
        for (Variant v : p.getVariant()) {
            for (Form f : v.getForm()) {
                String unstressed = StressUtils.unstress(f.getValue());
                String prevStresses = stressMap.get(unstressed);
                if (prevStresses == null) {
                    // яшчэ няма - дадаем
                    stressMap.put(unstressed, f.getValue());
                } else if (!prevStresses.equals(f.getValue())) {
                    // ужо ёсць, і несупадае
                    boolean[] stresses = StressUtils.getStressMap(prevStresses);
                    boolean[] newStresses = StressUtils.getStressMap(f.getValue());
                    if (stresses.length != newStresses.length) {
                        throw new Exception("stresses and stresses are not equal");
                    }
                    for (int i = 0; i < stresses.length; i++) {
                        stresses[i] |= newStresses[i];
                    }
                    String newValue = StressUtils.applyStressMap(unstressed, stresses);
                    stressMap.put(unstressed, newValue);
                }
            }
        }
    }

    Files.writeString(dbOutput, new Gson().toJson(stressMap));
    IO.println("Successfully wrote " + stressMap.size() + " stress entries to " + dbOutput.toAbsolutePath());

    Map<String, String> stressStat = new TreeMap<>();
    try (var in = this.getClass().getResourceAsStream("/amohrafy_naciski.txt");
         var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
        String line;
        while ((line = reader.readLine()) != null) {
            stressStat.put(line.replace("+", ""), line.replace("+", "\u0301"));
        }
    }

    Files.writeString(dbStatOutput, new Gson().toJson(stressStat));
    IO.println("Successfully wrote " + stressStat.size() + " stress entries to " + dbStatOutput.toAbsolutePath());
}
