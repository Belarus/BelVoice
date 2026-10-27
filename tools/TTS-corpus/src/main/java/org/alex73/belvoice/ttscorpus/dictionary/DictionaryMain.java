package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.fanetyka.impl.FanetykaConfig;
import org.alex73.fanetyka.impl.str.ToStringIPA;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.GrammarFinder;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Set;

/**
 * Usage: DictionaryMain <grammardb-dir> <dictionary.tsv> <pairsPerCombination> <maxPairs> <limitWords>
 * If dictionary.tsv exists it is loaded, otherwise built and saved.
 */
public class DictionaryMain {
    static void main(String[] args) throws Exception {
        if (args.length != 5) {
            System.err.println("Usage: DictionaryMain <grammardb-dir> <dictionary.tsv> <pairsPerCombination> <maxPairs> <limitWords>");
            System.exit(1);
        }
        String dbDir = args[0];
        Path file = Path.of(args[1]);
        int pairsPerCombination;
        long maxPairs;
        int limitWords;
        pairsPerCombination = Integer.parseInt(args[2]);
        if (pairsPerCombination < 1 || pairsPerCombination > 1_000_000) {
            System.err.println("pairsPerCombination must be between 1 and 1_000_000");
            System.exit(1);
        }
        maxPairs = Long.parseLong(args[3]);
        limitWords = Integer.parseInt(args[4]);

        GrammarDB2 db = GrammarDB2.initializeFromDir(dbDir);
        Set<String> words = GrammarWordLoader.load(db);
        var list = new ArrayList<>(words);
        if (limitWords > 0 && list.size() > limitWords) {
            list = new ArrayList<>(list.subList(0, limitWords));
        }
        G2PService g2p = new G2PService(new FanetykaConfig(new GrammarFinder(db)));
        new DictionaryBuilder(g2p, pairsPerCombination, maxPairs).build(list, file);

        System.err.println("Dictionary built successfully.");
    }
}
