package org.alex73.belvoice.ttscorpus.dictionary;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.alex73.belvoice.ttscorpus.model.Feature;
import org.alex73.belvoice.ttscorpus.model.FeatureType;

/** Inverted index feature -> words / "word1 word2" keys. */
public class Dictionary {
    public final Map<FeatureType, Map<String, List<String>>> invertedIndex = new EnumMap<>(FeatureType.class);

    public Dictionary() {
        for (FeatureType type : FeatureType.values()) {
            invertedIndex.put(type, new ConcurrentHashMap<>());
        }
    }

    public void addFeatures(String word, FeatureType type, String semicolonValues) {
        if (semicolonValues == null || semicolonValues.isEmpty()) {
            return;
        }
        word = word.intern();
        Map<String, List<String>> typeIndex = invertedIndex.get(type);
        int len = semicolonValues.length();
        int start = 0;
        for (int i = 0; i <= len; i++) {
            if (i == len || semicolonValues.charAt(i) == ';') {
                if (i > start) {
                    String val = semicolonValues.substring(start, i).intern();
                    typeIndex.computeIfAbsent(val, k -> Collections.synchronizedList(new ArrayList<>())).add(word);
                }
                start = i + 1;
            }
        }
    }

    public List<String> getWordsByFeature(FeatureType type, String value) {
        Map<String, List<String>> typeIndex = invertedIndex.get(type);
        if (typeIndex != null) {
            List<String> list = typeIndex.get(value);
            if (list != null) {
                return list;
            }
        }
        return Collections.emptyList();
    }

    public List<String> getWordsByFeature(Feature feature) {
        return getWordsByFeature(feature.type(), feature.value());
    }
}
