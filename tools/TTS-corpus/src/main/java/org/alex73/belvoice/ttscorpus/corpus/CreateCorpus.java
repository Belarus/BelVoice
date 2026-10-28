package org.alex73.belvoice.ttscorpus.corpus;

import org.alex73.belvoice.ttscorpus.dictionary.FeatureExtractor;
import org.alex73.belvoice.ttscorpus.dictionary.G2PService;
import org.alex73.belvoice.ttscorpus.model.Feature;
import org.alex73.belvoice.ttscorpus.model.FeatureType;
import org.alex73.fanetyka.impl.FanetykaConfig;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.GrammarFinder;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Стварэнне корпуса TTS з тэкставых файлаў па прагным алгарытме (Greedy Algorithm).
 */
public class CreateCorpus {

    public static final Map<FeatureType, Double> DEFAULT_FEATURE_WEIGHTS = Map.of(
            FeatureType.DIPHONE, 100.0,
            FeatureType.TRIPHONE, 10.0
    );

    private final G2PService g2p;
    private final Map<FeatureType, Double> featureWeights;

    public record Candidate(String line, List<String> words, Set<Feature> features) {
    }

    public CreateCorpus(G2PService g2p) {
        this(g2p, DEFAULT_FEATURE_WEIGHTS);
    }

    public CreateCorpus(G2PService g2p, Map<FeatureType, Double> featureWeights) {
        this.g2p = Objects.requireNonNull(g2p, "g2p");
        Map<FeatureType, Double> weights = new EnumMap<>(FeatureType.class);
        for (FeatureType type : FeatureType.values()) {
            weights.put(type, featureWeights.getOrDefault(type, 0.0));
        }
        this.featureWeights = Collections.unmodifiableMap(weights);
    }

    /**
     * Вылучае словы з радка. Можа быць перавызначаны ці пашыраны пазней.
     */
    public List<String> extractWords(String line) {
        if (line == null) {
            return Collections.emptyList();
        }
        String trimmed = line.trim();
        if (trimmed.isEmpty()) {
            return Collections.emptyList();
        }
        // Выдаляем нелітарныя знакі (акрамя націску \u0301, злучка і апострафа), разбіваем па прабелах
        String[] tokens = trimmed.split("[\\s\\p{Punct}&&[^-'\u0301]]+");
        List<String> words = new ArrayList<>(tokens.length);
        for (String t : tokens) {
            String w = t.trim();
            if (!w.isEmpty()) {
                words.add(w);
            }
        }
        return words;
    }

    /**
     * Стварае аб'ект Candidate для радка.
     */
    public Candidate createCandidate(String line) {
        String trimmed = line.trim();
        List<String> words = extractWords(trimmed);
        if (words.isEmpty()) {
            return null;
        }
        G2PService.PhoneticResult result = g2p.transcribe(words);
        Set<Feature> features = FeatureExtractor.extractFeatures(String.join(" ", words), result);
        return new Candidate(trimmed, words, features);
    }

    /**
     * Вылічвае карыснасць (score) кандыдата з улікам квадратычнага змяншэння вагі:
     * baseWeight / ((1 + count) * (1 + count)), нармалізаваную на колькасць слоў.
     */
    public double calculateScore(Candidate candidate, Map<Feature, Integer> corpusFeatureCounts) {
        if (candidate.words().isEmpty()) {
            return 0.0;
        }
        double totalWeight = 0.0;
        for (Feature f : candidate.features()) {
            double baseWeight = featureWeights.getOrDefault(f.type(), 0.0);
            if (baseWeight > 0.0) {
                int count = corpusFeatureCounts.getOrDefault(f, 0);
                long denom = (long) (1 + count) * (1 + count);
                totalWeight += (baseWeight / denom);
            }
        }
        return totalWeight / candidate.words().size();
    }

    /**
     * Выконвае прагны адбор сказаў-кандыдатаў.
     *
     * @param candidates       спіс кандыдатаў
     * @param initialLines     радкі, якія ўжо знаходзяцца ў корпусе
     * @param maxLinesToSelect максімальная колькасць новых радкоў для адбору (<= 0 без ліміту)
     * @return спіс новаадабраных радкоў
     */
    public List<Candidate> selectCorpus(Set<Candidate> candidates, Set<String> initialLines, int maxLinesToSelect) {
        Map<Feature, Integer> corpusFeatureCounts = new HashMap<>();
        Set<String> corpusLines = new HashSet<>(initialLines);

        // Ініцыялізуем лічыльнікі прыкмет па існуючых радках
        for (String line : initialLines) {
            try {
                Candidate c = createCandidate(line);
                if (c != null) {
                    for (Feature f : c.features()) {
                        corpusFeatureCounts.merge(f, 1, Integer::sum);
                    }
                }
            } catch (Exception e) {
                System.err.println("Failed to transcribe initial line: " + line + " (" + e.getMessage() + ")");
            }
        }

        // Адсякаем кандыдатаў, якія ўжо прысутнічаюць у корпусе
        List<Candidate> pool = new ArrayList<>();
        for (Candidate c : candidates) {
            if (c != null && !corpusLines.contains(c.line())) {
                pool.add(c);
            }
        }

        List<Candidate> selected = new ArrayList<>();
        int targetCount = (maxLinesToSelect > 0) ? maxLinesToSelect : pool.size();

        while (!pool.isEmpty() && selected.size() < targetCount) {
            int bestIdx = -1;
            double bestScore = -1.0;

            for (int i = 0; i < pool.size(); i++) {
                Candidate c = pool.get(i);
                double score = calculateScore(c, corpusFeatureCounts);
                if (score > bestScore) {
                    bestScore = score;
                    bestIdx = i;
                }
            }

            if (bestIdx < 0 || bestScore <= 0.0) {
                // Больш няма сказаў з карыснымі прыкметамі
                break;
            }

            Candidate chosen = pool.remove(bestIdx);
            selected.add(chosen);
            corpusLines.add(chosen.line());
            for (Feature f : chosen.features()) {
                corpusFeatureCounts.merge(f, 1, Integer::sum);
            }
        }

        return selected;
    }

    /**
     * Стварае або дапаўняе корпус з каталога тэкстаў у файл.
     */
    public void generateCorpus(Path inputDir, Path outputFile, int maxLines) throws Exception {
        Set<String> existingLines;
        if (Files.exists(outputFile)) {
            existingLines = Files.readAllLines(outputFile, StandardCharsets.UTF_8).stream()
                    .map(String::trim)
                    .collect(Collectors.toSet());
        } else {
            existingLines = new HashSet<>();
        }
        System.out.println("Існуючых радкоў у корпусе: " + existingLines.size());

        Set<Candidate> rawCandidateLines = Files.walk(inputDir)
                .filter(Files::isRegularFile)
                .flatMap(file -> {
                    try {
                        return Files.lines(file, StandardCharsets.UTF_8);
                    } catch (IOException e) {
                        throw new UncheckedIOException("Error reading file: " + file, e);
                    }
                })
                .map(String::trim)
                .filter(line -> !line.isEmpty())
                .map(line -> {
                    try {
                        return createCandidate(line);
                    } catch (Exception e) {
                        System.err.println("Failed to transcribe line: " + line + " (" + e.getMessage() + ")");
                        return null;
                    }
                })
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        System.out.println("Прачытана унікальных радкоў-кандыдатаў з каталога: " + rawCandidateLines.size());

        rawCandidateLines.removeAll(existingLines);
        System.out.println("Пасля выдалення існуючых радкоў-кандыдатаў: " + rawCandidateLines.size());

        List<Candidate> selected = selectCorpus(rawCandidateLines, existingLines, maxLines);
        System.out.println("Адабрана новых радкоў: " + selected.size());

        if (outputFile.getParent() != null) {
            Files.createDirectories(outputFile.getParent());
        }

        try (BufferedWriter writer = Files.newBufferedWriter(
                outputFile,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND)) {
            for (Candidate c : selected) {
                writer.write(c.line());
                writer.newLine();
            }
        }
        System.out.println("Запісана ў " + outputFile);
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 3 || args.length > 4) {
            System.err.println("Usage: CreateCorpus <grammardb-dir> <input-texts-dir> <output-corpus-file> [max-lines]");
            System.exit(1);
        }

        Path dbDir = Path.of(args[0]);
        Path inputDir = Path.of(args[1]);
        Path outputFile = Path.of(args[2]);
        int maxLines = (args.length == 4) ? Integer.parseInt(args[3]) : 0;

        System.out.println("Ініцыялізацыя GrammarDB...");
        GrammarDB2 db = GrammarDB2.initializeFromDir(dbDir.toString());
        G2PService g2p = new G2PService(new FanetykaConfig(new GrammarFinder(db)));

        CreateCorpus corpusCreator = new CreateCorpus(g2p);
        corpusCreator.generateCorpus(inputDir, outputFile, maxLines);
    }
}
