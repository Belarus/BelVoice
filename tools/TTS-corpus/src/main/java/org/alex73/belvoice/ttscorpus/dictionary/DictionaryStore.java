package org.alex73.belvoice.ttscorpus.dictionary;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.EnumMap;
import java.util.Map;

import org.alex73.belvoice.ttscorpus.model.FeatureType;

/** dictionary.tsv: words and boundary pairs with phonetic transcription and features. */
public class DictionaryStore {

    public static void save(Dictionary dict, Path file) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(file, StandardCharsets.UTF_8)) {
            writer.write(DictionaryBuilder.HEADER);
            writer.newLine();
            for (Map.Entry<String, Map<FeatureType, String>> entry : dict.words.entrySet()) {
                String word = entry.getKey();
                Map<FeatureType, String> features = entry.getValue();
                String diphone = features != null ? features.getOrDefault(FeatureType.DIPHONE, "") : "";
                String triphone = features != null ? features.getOrDefault(FeatureType.TRIPHONE, "") : "";
                String phoneticRule = features != null ? features.getOrDefault(FeatureType.PHONETIC_RULE, "") : "";
                writer.write(String.format("%s\t%s\t%s\t%s\t%s\t%s",
                        "", // group
                        word != null ? word : "",
                        "", // transcription
                        diphone != null ? diphone : "",
                        triphone != null ? triphone : "",
                        phoneticRule != null ? phoneticRule : ""));
                writer.newLine();
            }
        }
    }

    public static Dictionary load(Path file) throws IOException {
        Dictionary dict = new Dictionary();
        try (BufferedReader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                return dict;
            }
            String[] headers = headerLine.split("\t", -1);
            int wordsIdx = -1;
            int diphoneIdx = -1;
            int triphoneIdx = -1;
            int ruleIdx = -1;

            for (int i = 0; i < headers.length; i++) {
                String h = headers[i].trim();
                if ("WORDS".equalsIgnoreCase(h)) {
                    wordsIdx = i;
                } else if ("DIPHONE".equalsIgnoreCase(h)) {
                    diphoneIdx = i;
                } else if ("TRIPHONE".equalsIgnoreCase(h)) {
                    triphoneIdx = i;
                } else if ("PHONETIC_RULE".equalsIgnoreCase(h)) {
                    ruleIdx = i;
                }
            }

            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty()) {
                    continue;
                }
                String[] parts = line.split("\t", -1);
                String word = (wordsIdx >= 0 && wordsIdx < parts.length) ? parts[wordsIdx] : "";
                if (word.isEmpty()) {
                    continue;
                }

                Map<FeatureType, String> features = new EnumMap<>(FeatureType.class);
                if (diphoneIdx >= 0 && diphoneIdx < parts.length && !parts[diphoneIdx].isEmpty()) {
                    features.put(FeatureType.DIPHONE, parts[diphoneIdx]);
                }
                if (triphoneIdx >= 0 && triphoneIdx < parts.length && !parts[triphoneIdx].isEmpty()) {
                    features.put(FeatureType.TRIPHONE, parts[triphoneIdx]);
                }
                if (ruleIdx >= 0 && ruleIdx < parts.length && !parts[ruleIdx].isEmpty()) {
                    features.put(FeatureType.PHONETIC_RULE, parts[ruleIdx]);
                }

                dict.words.put(word, features);
            }
        }
        dict.rebuildIndex();
        return dict;
    }
}
