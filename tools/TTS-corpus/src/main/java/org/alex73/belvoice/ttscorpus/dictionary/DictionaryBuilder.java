package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.belvoice.ttscorpus.model.WordData;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Модуль 1: будуе слоўнік з прыкметамі асобных слоў і стыкаў слоў і паточна запісвае ў TSV.
 * <p>
 * TODO: выкарыстоўваць частотны слоўнік для выбару найбольш частых слоў для стыкаў, каб не перагружаць слоўнік рэдкімі словамі.
 */
public class DictionaryBuilder {
    public static final String HEADER = "GROUP\tWORDS\tTRANSCRIPTION\tDIGRAPH\tTRIGRAPH\tDIPHONE\tTRIPHONE\tPHONETIC_RULE";
    public static final String CLUSTERS_HEADER = "GROUP\tEXAMPLES";

    private final G2PService g2p;
    /**
     * Колькасць пар слоў для адной камбінацыі мяжы стыку.
     */
    private final int pairsPerCombination;
    /**
     * Максімальная агульная колькасць пар слоў.
     */
    private final long maxPairs;

    private final Random random = new Random();

    /**
     * Унікальныя дыграфы, якія сустракаюцца ў слоўніку - толькі для падліку статыстыкі.
     */
    private final Set<String> uniqueDigraphs = ConcurrentHashMap.newKeySet();
    /**
     * Унікальныя трыграфы, якія сустракаюцца ў слоўніку - толькі для падліку статыстыкі.
     */
    private final Set<String> uniqueTrigraphs = ConcurrentHashMap.newKeySet();
    /**
     * Унікальныя дыфоны, якія сустракаюцца ў слоўніку - толькі для падліку статыстыкі.
     */
    private final Set<String> uniqueDiphones = ConcurrentHashMap.newKeySet();
    /**
     * Унікальныя трыфоны, якія сустракаюцца ў слоўніку - толькі для падліку статыстыкі.
     */
    private final Set<String> uniqueTriphones = ConcurrentHashMap.newKeySet();

    /**
     * Кластэрызацыя па літарах на сутыку: камбінацыя літар -> прыклады пар слоў (да 5).
     */
    private final Map<String, Set<String>> letterClusters = new ConcurrentHashMap<>();
    /**
     * Кластэрызацыя па гуках (токенах) на сутыку: камбінацыя токенаў -> прыклады пар слоў (да 5).
     */
    private final Map<String, Set<String>> tokenClusters = new ConcurrentHashMap<>();

    private BufferedWriter writer;
    /**
     * Захоўвае словы для праверкі BelG2P.
     */
    private BufferedWriter wordsWriter;

    public DictionaryBuilder(G2PService g2p, int pairsPerCombination, long maxPairs) {
        this.g2p = g2p;
        this.pairsPerCombination = pairsPerCombination > 0 ? pairsPerCombination : 50;
        this.maxPairs = maxPairs;
    }

    /**
     * Будуе слоўнік на аснове спіса ўнікальных слоў і паточна запісвае яго ў TSV файл,
     * а таксама захоўвае файлы кластэрызацыі па літарах і токенах на сутыку.
     */
    public void build(Collection<String> uniqueWords, Path outputFile) throws Exception {
        uniqueDigraphs.clear();
        uniqueTrigraphs.clear();
        uniqueDiphones.clear();
        uniqueTriphones.clear();
        letterClusters.clear();
        tokenClusters.clear();
        this.writer = Files.newBufferedWriter(outputFile, StandardCharsets.UTF_8);
        this.wordsWriter = Files.newBufferedWriter(resolveSibling(outputFile, "grammardb.txt"), StandardCharsets.UTF_8);
        writer.write(HEADER);
        writer.newLine();

        processWords(uniqueWords);
        processBoundaries(uniqueWords);
        writer.close();
        wordsWriter.close();

        writeClustersFile(letterClusters, resolveSibling(outputFile, "clusters_letters.tsv"));
        writeClustersFile(tokenClusters, resolveSibling(outputFile, "clusters_tokens.tsv"));

        System.out.println("Унікальных дыграфаў: " + uniqueDigraphs.size() + ", унікальных трыграфаў: " + uniqueTrigraphs.size() + ", унікальных дыфонаў: " + uniqueDiphones.size() + ", унікальных трыфонаў: " + uniqueTriphones.size());
    }

    private Path resolveSibling(Path outputFile, String fileName) {
        Path parent = outputFile.getParent();
        return parent != null ? parent.resolve(fileName) : Path.of(fileName);
    }

    private void writeClustersFile(Map<String, Set<String>> clusters, Path path) throws IOException {
        Map<String, Set<String>> sorted = new TreeMap<>(clusters);
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            writer.write(CLUSTERS_HEADER);
            writer.newLine();
            for (Map.Entry<String, Set<String>> entry : sorted.entrySet()) {
                String examples = String.join("; ", entry.getValue().stream().limit(5).toList());
                writer.write(entry.getKey() + "\t" + examples);
                writer.newLine();
            }
        }
    }

    private void recordClusterExample(Map<String, Set<String>> clusters, String group, String example) {
        if (group == null) {
            return;
        }
        clusters.compute(group, (k, existing) -> {
            if (existing == null) {
                existing = Collections.synchronizedSet(new LinkedHashSet<>());
            }
            if (existing.size() < 5) {
                existing.add(example);
            }
            return existing;
        });
    }

    private void writeRow(WordData data) {
        collectStat(data);
        String line = String.format("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s",
                data.group() != null ? data.group() : "",
                data.words() != null ? data.words() : "",
                data.phoneticTranscription() != null ? data.phoneticTranscription() : "",
                data.digraph() != null ? data.digraph() : "",
                data.trigraph() != null ? data.trigraph() : "",
                data.diphone() != null ? data.diphone() : "",
                data.triphone() != null ? data.triphone() : "",
                data.phoneticRule() != null ? data.phoneticRule() : "");
        synchronized (writer) {
            try {
                writer.write(line);
                writer.newLine();
            } catch (IOException e) {
                throw new RuntimeException("Error writing to TSV: " + e.getMessage(), e);
            }
        }
    }

    private void writeWords(String words) {
        synchronized (wordsWriter) {
            try {
                wordsWriter.write(words);
                wordsWriter.newLine();
            } catch (IOException e) {
                throw new RuntimeException("Error writing to words file: " + e.getMessage(), e);
            }
        }
    }

    private void collectStat(WordData data) {
        if (data.digraph() != null && !data.digraph().isEmpty()) {
            for (String d : data.digraph().split(";")) {
                if (!d.isEmpty()) {
                    uniqueDigraphs.add(d);
                }
            }
        }
        if (data.trigraph() != null && !data.trigraph().isEmpty()) {
            for (String t : data.trigraph().split(";")) {
                if (!t.isEmpty()) {
                    uniqueTrigraphs.add(t);
                }
            }
        }
        if (data.diphone() != null && !data.diphone().isEmpty()) {
            for (String d : data.diphone().split(";")) {
                if (!d.isEmpty()) {
                    uniqueDiphones.add(d);
                }
            }
        }
        if (data.triphone() != null && !data.triphone().isEmpty()) {
            for (String t : data.triphone().split(";")) {
                if (!t.isEmpty()) {
                    uniqueTriphones.add(t);
                }
            }
        }
    }

    /**
     * Апрацоўка асобных слоў: фанетычная транскрыпцыя і выманне features праз G2P.
     */
    void processWords(Collection<String> words) {
        words.parallelStream().forEach(word -> {
            try {
                writeWords(word);
                G2PService.PhoneticResult r = g2p.transcribe(List.of(word));
                WordData data = new WordData(word);
                FeatureExtractor.fillFeatures(data, r);
                writeRow(data);
            } catch (Exception ex) {
                throw new RuntimeException("G2P error for word '" + word + "': " + ex.getMessage(), ex);
            }
        });
    }

    /**
     * Групуе словы па канчатках (tail) і пачатках (head) ды фармуе пары для кожнай мяжы.
     */
    void processBoundaries(Collection<String> words) {
        Map<String, List<String>> tailGroups = new TreeMap<>();
        Map<String, List<String>> headGroups = new TreeMap<>();
        // Размяркоўваем словы па групах канчаткаў і пачаткаў
        for (String w : words) {
            String tail = BoundaryClustering.tail(w, false);
            String head = BoundaryClustering.head(w, false);
            if (tail != null) {
                tailGroups.computeIfAbsent(tail, k -> new ArrayList<>()).add(w);
            }
            if (head != null) {
                headGroups.computeIfAbsent(head, k -> new ArrayList<>()).add(w);
            }
        }

        // Для кожнай камбінацыі "хвост + пачатак" фармуем пары слоў
        AtomicLong totalPairsWritten = new AtomicLong(0);
        for (Map.Entry<String, List<String>> te : tailGroups.entrySet()) {
            List<String> tailWords = te.getValue();
            for (Map.Entry<String, List<String>> he : headGroups.entrySet()) {
                if (maxPairs > 0 && totalPairsWritten.get() >= maxPairs) {
                    return;
                }
                List<String> headWords = he.getValue();
                String group = te.getKey() + " " + he.getKey();
                processPairs(group, tailWords, headWords, totalPairsWritten);
            }
        }
    }

    /**
     * Выбірае пары слоў для канкрэтнага сутыку і апрацоўвае іх.
     */
    private void processPairs(String group, List<String> tailWords, List<String> headWords,
                              AtomicLong totalPairsWritten) {
        List<String[]> pairs = new ArrayList<>();
        long totalPossible = (long) tailWords.size() * headWords.size();
        if (totalPossible <= pairsPerCombination) {
            // Калі магчымых пар менш ці роўна за ліміт, бяром усе камбінацыі
            for (String tw : tailWords) {
                for (String hw : headWords) {
                    pairs.add(new String[]{tw, hw});
                }
            }
        } else {
            // Інакш выбіраем выпадковыя пары без паўтораў
            Set<String> chosenKeys = new HashSet<>();
            int attempts = 0;
            int maxAttempts = pairsPerCombination * 10;
            while (chosenKeys.size() < pairsPerCombination && attempts < maxAttempts) {
                attempts++;
                String tw;
                String hw;
                synchronized (random) {
                    tw = tailWords.get(random.nextInt(tailWords.size()));
                    hw = headWords.get(random.nextInt(headWords.size()));
                }
                if (chosenKeys.add(tw + "\t" + hw)) {
                    pairs.add(new String[]{tw, hw});
                }
            }
        }

        pairs.parallelStream().forEach(pair -> {
            if (maxPairs > 0 && totalPairsWritten.get() >= maxPairs) {
                return;
            }
            try {
                writeWords(pair[0] + " " + pair[1]);
                G2PService.PhoneticResult r = g2p.transcribe(List.of(pair[0], pair[1]));
                WordData data = new WordData(pair[0] + " " + pair[1]);
                data.setGroup(group);
                FeatureExtractor.fillFeatures(data, r);
                writeRow(data);
                totalPairsWritten.incrementAndGet();

                String pairWords = pair[0] + " " + pair[1];
                recordClusterExample(letterClusters, BoundaryClustering.letterBoundary(pair[0], pair[1]), pairWords);
                recordClusterExample(tokenClusters, BoundaryClustering.tokenBoundary(r.transcription()), pairWords);
            } catch (Exception ex) {
                // TODO выправіць за́гс з-за́
                System.out.println("G2P error for pair '" + pair[0] + " " + pair[1] + "': " + ex.getMessage());
            }
        });
    }
}
