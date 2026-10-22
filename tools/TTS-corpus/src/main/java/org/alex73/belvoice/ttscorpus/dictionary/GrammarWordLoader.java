package org.alex73.belvoice.ttscorpus.dictionary;

import org.alex73.grammardb.FormsReadyFilter;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.structures.Paradigm;
import org.alex73.grammardb.structures.Variant;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * Загружае ўнікальныя словы з GrammarDB2, з фільтраваннем слоў па слоўніках.
 */
public final class GrammarWordLoader {
    private GrammarWordLoader() {
    }

    public static Set<String> load(GrammarDB2 db) {
        Set<String> words = new TreeSet<>();
        for (Paradigm p : db.getAllParadigms()) {
            for (Variant v : p.getVariant()) {
                List<Form> forms = FormsReadyFilter.getAcceptedForms(FormsReadyFilter.MODE.SPELL, p, v);
                if (forms != null) {
                    for (Form f : forms) {
                        String w = normalize(f.getValue());
                        if (w != null) {
                            words.add(w);
                        }
                    }
                }
            }
        }
        return words;
    }

    /**
     * Lowercase, '+' stress to U+0301; null if empty.
     */
    static String normalize(String s) {
        if (s == null || s.isEmpty() || s.indexOf(' ') >= 0 || s.indexOf('.') >= 0) {
            return null; // адкідаем словы з прагаламі і кропкамі TODO
        }
        return s.toLowerCase();
    }
}
