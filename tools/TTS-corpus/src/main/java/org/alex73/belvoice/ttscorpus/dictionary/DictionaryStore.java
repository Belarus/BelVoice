package org.alex73.belvoice.ttscorpus.dictionary;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import org.alex73.belvoice.ttscorpus.model.FeatureType;

/** dictionary.tsv: words and boundary pairs with phonetic transcription and features. */
public class DictionaryStore {

    public static Dictionary load(Path file) throws IOException {
        Dictionary dict = new Dictionary();
        try (BufferedReader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                return dict;
            }
            String[] headers = headerLine.split("\t", -1);
            int wordsIdx = -1;
            int digraphIdx = -1;
            int trigraphIdx = -1;
            int diphoneIdx = -1;
            int triphoneIdx = -1;
            int ruleIdx = -1;

            for (int i = 0; i < headers.length; i++) {
                String h = headers[i].trim();
                if ("WORDS".equalsIgnoreCase(h)) {
                    wordsIdx = i;
                } else if ("DIGRAPH".equalsIgnoreCase(h)) {
                    digraphIdx = i;
                } else if ("TRIGRAPH".equalsIgnoreCase(h)) {
                    trigraphIdx = i;
                } else if ("DIPHONE".equalsIgnoreCase(h)) {
                    diphoneIdx = i;
                } else if ("TRIPHONE".equalsIgnoreCase(h)) {
                    triphoneIdx = i;
                } else if ("PHONETIC_RULE".equalsIgnoreCase(h)) {
                    ruleIdx = i;
                }
            }

            final int finalWordsIdx = wordsIdx;
            final int finalDigraphIdx = digraphIdx;
            final int finalTrigraphIdx = trigraphIdx;
            final int finalDiphoneIdx = diphoneIdx;
            final int finalTriphoneIdx = triphoneIdx;
            final int finalRuleIdx = ruleIdx;

            reader.lines().parallel().forEach(line -> {
                if (line.isEmpty()) {
                    return;
                }
                parseLine(line, dict, finalWordsIdx, finalDigraphIdx, finalTrigraphIdx,
                        finalDiphoneIdx, finalTriphoneIdx, finalRuleIdx);
            });
        }
        return dict;
    }

    private static void parseLine(String line, Dictionary dict, int wordsIdx, int digraphIdx,
                                  int trigraphIdx, int diphoneIdx, int triphoneIdx, int ruleIdx) {
        int maxCol = Math.max(wordsIdx, Math.max(digraphIdx, Math.max(trigraphIdx,
                Math.max(diphoneIdx, Math.max(triphoneIdx, ruleIdx)))));
        if (maxCol < 0) {
            return;
        }

        int col = 0;
        int start = 0;
        int len = line.length();

        String word = null;
        String digraph = null;
        String trigraph = null;
        String diphone = null;
        String triphone = null;
        String rule = null;

        for (int i = 0; i <= len; i++) {
            if (i == len || line.charAt(i) == '\t') {
                if (col == wordsIdx && i > start) {
                    word = line.substring(start, i);
                } else if (col == digraphIdx && i > start) {
                    digraph = line.substring(start, i);
                } else if (col == trigraphIdx && i > start) {
                    trigraph = line.substring(start, i);
                } else if (col == diphoneIdx && i > start) {
                    diphone = line.substring(start, i);
                } else if (col == triphoneIdx && i > start) {
                    triphone = line.substring(start, i);
                } else if (col == ruleIdx && i > start) {
                    rule = line.substring(start, i);
                }
                col++;
                start = i + 1;
            }
        }

        if (word == null || word.isEmpty()) {
            return;
        }

        dict.addFeatures(word, FeatureType.DIGRAPH, digraph);
        dict.addFeatures(word, FeatureType.TRIGRAPH, trigraph);
        dict.addFeatures(word, FeatureType.DIPHONE, diphone);
        dict.addFeatures(word, FeatureType.TRIPHONE, triphone);
        dict.addFeatures(word, FeatureType.PHONETIC_RULE, rule);
    }
}

