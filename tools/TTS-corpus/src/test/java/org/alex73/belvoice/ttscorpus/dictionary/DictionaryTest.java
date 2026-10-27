package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.belvoice.ttscorpus.model.Feature;
import org.alex73.belvoice.ttscorpus.model.FeatureType;
import org.alex73.belvoice.ttscorpus.model.WordData;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class DictionaryTest {
    @Test
    void headTail() {
        assertEquals("спрэ", BoundaryClustering.head("спрэчка", false));
        assertEquals("спрэ\u0301", BoundaryClustering.head("спрэ\u0301чка", false));
        assertEquals("ождж", BoundaryClustering.tail("дождж", false));
        assertEquals("о\u0301ждж", BoundaryClustering.tail("до\u0301ждж", false));
        assertEquals("ўў", BoundaryClustering.head("ўў", false));
        assertEquals("ст", BoundaryClustering.tail("ст", false));

        assertEquals("спр", BoundaryClustering.head("спрэчка", true));
        assertEquals("спр", BoundaryClustering.head("спрэ\u0301чка", true));
        assertEquals("", BoundaryClustering.head("аблокі", true));
        assertEquals("ждж", BoundaryClustering.tail("дождж", true));
        assertEquals("ждж", BoundaryClustering.tail("до\u0301ждж", true));
        assertEquals("", BoundaryClustering.tail("рака", true));
    }

    @Test
    void normalize() {
        assertEquals("аага\u0301мны", GrammarWordLoader.normalize("Аага\u0301мны"));
        assertNull(GrammarWordLoader.normalize(""));
        assertNull(GrammarWordLoader.normalize(null));
    }

    @Test
    void features() {
        G2PService.PhoneticResult r = new G2PService.PhoneticResult("аб вг", List.of("R: x"));
        WordData data = new WordData("аб вг");
        FeatureExtractor.fillFeatures(data, r);
        assertEquals("аб;б в;вг", data.digraph());
        assertEquals("аб в;б вг", data.trigraph());
        assertEquals("аб;б в;вг", data.diphone());
        assertEquals("аб в;б вг", data.triphone());
        assertEquals("R: x", data.phoneticRule());
    }

    @Test
    void textWindows() {
        List<String> d = FeatureExtractor.textWindows("рака аблокі", 2);
        assertEquals(List.of("ра", "ак", "ка", "а а", "аб", "бл", "ло", "ок", "кі"), d);

        List<String> tr = FeatureExtractor.textWindows("рака аблокі", 3);
        assertEquals(List.of("рак", "ака", "ка а", "а аб", "абл", "бло", "лок", "окі"), tr);
    }

    @Test
    void textWindowsWithStressMark() {
        List<String> d = FeatureExtractor.textWindows("до\u0301ждж спрэ\u0301чка", 2);
        assertEquals(List.of("до\u0301", "о\u0301ж", "жд", "дж", "ж с", "сп", "пр", "рэ\u0301", "э\u0301ч", "чк", "ка"), d);

        List<String> tr = FeatureExtractor.textWindows("до\u0301ждж спрэ\u0301чка", 3);
        assertEquals(List.of("до\u0301ж", "о\u0301жд", "ждж", "дж с", "ж сп", "спр", "прэ\u0301", "рэ\u0301ч", "э\u0301чк", "чка"), tr);
    }

    @Test
    void windowsWithSpaces() {
        byte[] tokens = org.alex73.fanetyka.impl.str.TokenStr.str2tokens("аб в г");
        List<String> d = FeatureExtractor.windows(tokens, 2);
        assertEquals(List.of("аб", "б в", "в г"), d);

        List<String> tr = FeatureExtractor.windows(tokens, 3);
        assertEquals(List.of("аб в", "б в г"), tr);

        List<String> four = FeatureExtractor.windows(tokens, 4);
        assertEquals(List.of("аб в г"), four);

        List<String> five = FeatureExtractor.windows(tokens, 5);
        assertTrue(five.isEmpty());
    }

    @Test
    void storeRoundTrip(@TempDir Path dir) throws Exception {
        Dictionary d = new Dictionary();
        Feature f1 = new Feature(FeatureType.DIPHONE, "a-b");
        Feature f2 = new Feature(FeatureType.DIPHONE, "b-c");
        Feature fb = new Feature(FeatureType.DIPHONE, "b|b");
        Feature fd = new Feature(FeatureType.DIGRAPH, "аб");
        Feature ft = new Feature(FeatureType.TRIGRAPH, "абв");
        d.words.put("аб", Map.of(FeatureType.DIPHONE, "a-b;b-c", FeatureType.DIGRAPH, "аб"));
        d.words.put("аб ба", Map.of(FeatureType.DIPHONE, "b|b", FeatureType.TRIGRAPH, "абв"));
        Path file = dir.resolve("dictionary.tsv");
        DictionaryStore.save(d, file);
        Dictionary l = DictionaryStore.load(file);
        assertEquals(d.words, l.words);
        assertEquals(List.of("аб"), l.invertedIndex.get(f1));
        assertEquals(List.of("аб"), l.invertedIndex.get(f2));
        assertEquals(List.of("аб ба"), l.invertedIndex.get(fb));
        assertEquals(List.of("аб"), l.invertedIndex.get(fd));
        assertEquals(List.of("аб ба"), l.invertedIndex.get(ft));
    }

    @Test
    void processBoundariesAndWordsStreamedToTsv(@TempDir Path dir) throws Exception {
        G2PService mockG2p = new G2PService(null) {
            @Override
            public PhoneticResult transcribe(List<String> words) {
                if (words.size() == 1) {
                    return new PhoneticResult("аб", List.of());
                } else {
                    return new PhoneticResult("аб в", List.of("Rule: boundary"));
                }
            }
        };
        DictionaryBuilder builder = new DictionaryBuilder(mockG2p, 5, 0);
        Path file = dir.resolve("dictionary.tsv");
        builder.build(List.of("рака", "аблокі"), file);

        List<String> lines = java.nio.file.Files.readAllLines(file);
        assertEquals(DictionaryBuilder.HEADER, lines.get(0));
        assertTrue(lines.contains("\tрака\tаб\tра;ак;ка\tрак;ака\tаб\t\t"));
        assertTrue(lines.contains("\tаблокі\tаб\tаб;бл;ло;ок;кі\tабл;бло;лок;окі\tаб\t\t"));
        assertTrue(lines.contains("а а\tрака аблокі\tаб в\tра;ак;ка;а а;аб;бл;ло;ок;кі\tрак;ака;ка а;а аб;абл;бло;лок;окі\tаб;б в\tаб в\tRule: boundary"));

        Dictionary dict = DictionaryStore.load(file);
        assertTrue(dict.words.containsKey("рака"));
        assertTrue(dict.words.containsKey("аблокі"));
        assertTrue(dict.words.containsKey("рака аблокі"));

        Map<FeatureType, String> pairFeatures = dict.words.get("рака аблокі");
        assertNotNull(pairFeatures);
        assertEquals("ра;ак;ка;а а;аб;бл;ло;ок;кі", pairFeatures.get(FeatureType.DIGRAPH));
        assertEquals("рак;ака;ка а;а аб;абл;бло;лок;окі", pairFeatures.get(FeatureType.TRIGRAPH));
        assertEquals("аб;б в", pairFeatures.get(FeatureType.DIPHONE));
        assertEquals("аб в", pairFeatures.get(FeatureType.TRIPHONE));
        assertEquals("Rule: boundary", pairFeatures.get(FeatureType.PHONETIC_RULE));

        assertFalse(dict.invertedIndex.isEmpty());

        // Праверка файлаў кластэрызацыі
        Path lettersFile = dir.resolve("clusters_letters.tsv");
        Path tokensFile = dir.resolve("clusters_tokens.tsv");
        assertTrue(java.nio.file.Files.exists(lettersFile));
        assertTrue(java.nio.file.Files.exists(tokensFile));

        List<String> letterLines = java.nio.file.Files.readAllLines(lettersFile);
        assertEquals(DictionaryBuilder.CLUSTERS_HEADER, letterLines.get(0));
        assertTrue(letterLines.stream().anyMatch(l -> l.startsWith(" \t") && l.contains("рака аблокі")));

        List<String> tokenLines = java.nio.file.Files.readAllLines(tokensFile);
        assertEquals(DictionaryBuilder.CLUSTERS_HEADER, tokenLines.get(0));
        assertTrue(tokenLines.stream().anyMatch(l -> l.startsWith("б в\t") && l.contains("рака аблокі")));
    }

    @Test
    void boundaryClusteringLetters() {
        assertEquals("ждж спр", BoundaryClustering.letterBoundary("дождж", "спрэчка"));
        assertEquals("ждж спр", BoundaryClustering.letterBoundary("до\u0301ждж", "спрэ\u0301чка"));
        assertEquals(" ", BoundaryClustering.letterBoundary("рака", "аблокі"));
        assertEquals(" спр", BoundaryClustering.letterBoundary("рака", "спрэчка"));
        assertEquals("ждж ", BoundaryClustering.letterBoundary("дождж", "аблокі"));
        assertEquals("з л", BoundaryClustering.letterBoundary("з", "лесу"));
        assertEquals("л з", BoundaryClustering.letterBoundary("стол", "з"));
    }

    @Test
    void boundaryClusteringTokens() {
        assertEquals("б в", BoundaryClustering.tokenBoundary("аб в"));
        assertEquals(" ", BoundaryClustering.tokenBoundary("рака аблокі"));
        assertEquals("ждж спр", BoundaryClustering.tokenBoundary("дождж спрэчка"));
    }

    @Test
    void clustersFileLimitFiveExamples(@TempDir Path dir) throws Exception {
        G2PService mockG2p = new G2PService(null) {
            @Override
            public PhoneticResult transcribe(List<String> words) {
                return new PhoneticResult("аб в", List.of());
            }
        };
        DictionaryBuilder builder = new DictionaryBuilder(mockG2p, 10, 0);
        Path file = dir.resolve("dictionary.tsv");
        // Некалькі слоў з аднолькавымі канчаткамі і пачаткамі
        builder.build(List.of("к1а", "к2а", "к3а", "а1", "а2", "а3"), file);

        Path lettersFile = dir.resolve("clusters_letters.tsv");
        List<String> lines = java.nio.file.Files.readAllLines(lettersFile);
        for (String line : lines.subList(1, lines.size())) {
            String[] parts = line.split("\t", -1);
            assertEquals(2, parts.length);
            String[] examples = parts[1].split("; ");
            assertTrue(examples.length <= 5);
        }
    }
}
