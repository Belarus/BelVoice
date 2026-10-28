package org.alex73.belvoice.ttscorpus.corpus;

import org.alex73.belvoice.ttscorpus.dictionary.FeatureExtractor;
import org.alex73.belvoice.ttscorpus.dictionary.G2PService;
import org.alex73.belvoice.ttscorpus.model.Feature;
import org.alex73.belvoice.ttscorpus.model.FeatureType;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class CreateCorpusTest {

    static class MockG2PService extends G2PService {
        private final Map<String, String> transcriptions = new HashMap<>();

        public MockG2PService() {
            super(null);
        }

        public void mock(String words, String transcription) {
            transcriptions.put(words, transcription);
        }

        @Override
        public PhoneticResult transcribe(List<String> words) {
            String key = String.join(" ", words);
            String tr = transcriptions.getOrDefault(key, key);
            return new PhoneticResult(tr, List.of());
        }
    }

    @Test
    void extractWords() {
        CreateCorpus corpus = new CreateCorpus(new MockG2PService());
        List<String> words = corpus.extractWords("  Прывітанне, свет! Як справы?  ");
        assertEquals(List.of("Прывітанне", "свет", "Як", "справы"), words);

        List<String> withAccents = corpus.extractWords("до\u0301ждж ідзе\u0301, дзе\u0301ці.");
        assertEquals(List.of("до\u0301ждж", "ідзе\u0301", "дзе\u0301ці"), withAccents);

        assertTrue(corpus.extractWords("").isEmpty());
        assertTrue(corpus.extractWords(null).isEmpty());
    }

    @Test
    void featureExtractorSet() {
        G2PService.PhoneticResult r = new G2PService.PhoneticResult("аб вг", List.of("Rule1"));
        Set<Feature> features = FeatureExtractor.extractFeatures("аб вг", r);

        assertTrue(features.contains(new Feature(FeatureType.DIPHONE, "аб")));
        assertTrue(features.contains(new Feature(FeatureType.DIPHONE, "б в")));
        assertTrue(features.contains(new Feature(FeatureType.DIPHONE, "вг")));
        assertTrue(features.contains(new Feature(FeatureType.TRIPHONE, "аб в")));
        assertTrue(features.contains(new Feature(FeatureType.TRIPHONE, "б вг")));
        assertTrue(features.contains(new Feature(FeatureType.DIGRAPH, "аб")));
        assertTrue(features.contains(new Feature(FeatureType.PHONETIC_RULE, "Rule1")));
    }

    @Test
    void quadraticWeightDecay() {
        MockG2PService g2p = new MockG2PService();
        CreateCorpus corpus = new CreateCorpus(g2p);

        Feature d1 = new Feature(FeatureType.DIPHONE, "d1");
        Feature t1 = new Feature(FeatureType.TRIPHONE, "t1");

        CreateCorpus.Candidate c = new CreateCorpus.Candidate("line", List.of("w1"), Set.of(d1, t1));

        Map<Feature, Integer> counts = new HashMap<>();
        // count = 0: diphone (100 / 1^2) + triphone (10 / 1^2) = 110.0
        double score0 = corpus.calculateScore(c, counts);
        assertEquals(110.0, score0, 1e-6);

        // count = 1: diphone (100 / 2^2 = 25.0) + triphone (10 / 2^2 = 2.5) = 27.5
        counts.put(d1, 1);
        counts.put(t1, 1);
        double score1 = corpus.calculateScore(c, counts);
        assertEquals(27.5, score1, 1e-6);

        // count = 2: diphone (100 / 3^2 = 11.111...) + triphone (10 / 3^2 = 1.111...)
        counts.put(d1, 2);
        counts.put(t1, 2);
        double score2 = corpus.calculateScore(c, counts);
        assertEquals(110.0 / 9.0, score2, 1e-6);
    }

    @Test
    void lengthNormalization() {
        MockG2PService g2p = new MockG2PService();
        CreateCorpus corpus = new CreateCorpus(g2p);

        Feature d1 = new Feature(FeatureType.DIPHONE, "d1");

        CreateCorpus.Candidate shortCand = new CreateCorpus.Candidate("w1", List.of("w1"), Set.of(d1));
        CreateCorpus.Candidate longCand = new CreateCorpus.Candidate("w1 w2", List.of("w1", "w2"), Set.of(d1));

        Map<Feature, Integer> counts = new HashMap<>();
        double shortScore = corpus.calculateScore(shortCand, counts);
        double longScore = corpus.calculateScore(longCand, counts);

        // shortScore: 100 / 1 = 100, longScore: 100 / 2 = 50
        assertEquals(100.0, shortScore, 1e-6);
        assertEquals(50.0, longScore, 1e-6);
        assertTrue(shortScore > longScore);
    }

    @Test
    void lineDeduplicationAndResumingExistingFile(@TempDir Path tempDir) throws Exception {
        MockG2PService g2p = new MockG2PService();
        // Setup mock transcriptions to produce diphones
        g2p.mock("адзін", "ад зін");
        g2p.mock("два", "два");
        g2p.mock("тры", "тры");

        CreateCorpus corpus = new CreateCorpus(g2p);

        Path inputDir = tempDir.resolve("input");
        Files.createDirectories(inputDir);
        Path f1 = inputDir.resolve("texts1.txt");
        Path f2 = inputDir.resolve("texts2.txt");

        // Candidates contain duplicate lines and a line already in existing output file
        Files.writeString(f1, "адзін\nдва\nадзін\n");
        Files.writeString(f2, "два\nтры\n");

        Path outputFile = tempDir.resolve("corpus.txt");
        // Output file already exists with line "адзін"
        Files.writeString(outputFile, "адзін\n");

        corpus.generateCorpus(inputDir, outputFile, 0);

        List<String> outputLines = Files.readAllLines(outputFile);
        // "адзін" should not be duplicated, and "два", "тры" added exactly once
        assertEquals(3, outputLines.size());
        assertEquals("адзін", outputLines.get(0));
        assertTrue(outputLines.contains("два"));
        assertTrue(outputLines.contains("тры"));

        // No line occurs more than once
        Set<String> unique = new HashSet<>(outputLines);
        assertEquals(outputLines.size(), unique.size());
    }

    @Test
    void greedySelectionPrioritizesNewFeatures() {
        MockG2PService g2p = new MockG2PService();
        CreateCorpus corpus = new CreateCorpus(g2p);

        Feature d1 = new Feature(FeatureType.DIPHONE, "d1");
        Feature d2 = new Feature(FeatureType.DIPHONE, "d2");
        Feature d3 = new Feature(FeatureType.DIPHONE, "d3");

        CreateCorpus.Candidate c1 = new CreateCorpus.Candidate("line1", List.of("w1"), Set.of(d1, d2));
        CreateCorpus.Candidate c2 = new CreateCorpus.Candidate("line2", List.of("w2"), Set.of(d1));
        CreateCorpus.Candidate c3 = new CreateCorpus.Candidate("line3", List.of("w3"), Set.of(d3));

        List<CreateCorpus.Candidate> selected = corpus.selectCorpus(List.of(c1, c2, c3), Set.of(), 3);

        assertEquals(3, selected.size());
        // First must be c1 because it has 2 new diphones (score 200)
        assertEquals("line1", selected.get(0).line());
        // Second must be c3 because d3 is new (score 100), while c2 only has d1 which is already count=1 (score 25)
        assertEquals("line3", selected.get(1).line());
        // Third is c2
        assertEquals("line2", selected.get(2).line());
    }
}
