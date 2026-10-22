package org.alex73.belvoice.ttscorpus.dictionary;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import org.alex73.belvoice.ttscorpus.model.Feature;
import org.alex73.belvoice.ttscorpus.model.FeatureType;

/** Words (or "word1 word2" pairs) -> features, and inverted index feature -> words / "word1 word2" keys. */
public class Dictionary {
    public final Map<String, Map<FeatureType, String>> words = new TreeMap<>();
    public final Map<Feature, List<String>> invertedIndex = new HashMap<>();

    public void rebuildIndex() {
        invertedIndex.clear();
        for (Map.Entry<String, Map<FeatureType, String>> w : words.entrySet()) {
            String key = w.getKey();
            Map<FeatureType, String> features = w.getValue();
            if (features != null) {
                for (Map.Entry<FeatureType, String> e : features.entrySet()) {
                    if (e.getValue() != null && !e.getValue().isEmpty()) {
                        for (String val : e.getValue().split(";")) {
                            invertedIndex.computeIfAbsent(new Feature(e.getKey(), val), k -> new ArrayList<>())
                                    .add(key);
                        }
                    }
                }
            }
        }
    }
}
