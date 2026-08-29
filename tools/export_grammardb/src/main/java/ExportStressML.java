import org.alex73.grammardb.FormsReadyFilter;
import org.alex73.grammardb.GrammarDB2;
import org.alex73.grammardb.StressUtils;
import org.alex73.grammardb.structures.Form;
import org.alex73.grammardb.structures.Paradigm;
import org.alex73.grammardb.structures.Variant;

/**
 * Чытае граматычную базу і стварае stress.list — спіс усіх форм з націскам, згрупаваных па PDG_ID.
 * Кожны радок мае фармат "PDG_ID:форма1;форма2;...;формаN".
 */
void main() throws Exception {
    Path stressListOutput = Path.of("../stress_ml/stress.list");

    GrammarDB2 db = GrammarDB2.initializeFromDir("/home/alex/gits/GrammarDB/data");

    Set<String> forms = new TreeSet<>();
    int lines = 0;
    try (BufferedWriter bw = Files.newBufferedWriter(stressListOutput)) {
        for (Paradigm p : db.getAllParadigms()) {
            forms.clear();
            for (Variant v : p.getVariant()) {
                List<Form> accepted = FormsReadyFilter.getAcceptedForms(FormsReadyFilter.MODE.SPELL, p, v);
                if (accepted == null) {
                    continue;
                }
                for (Form f : accepted) {
                    if (!StressUtils.hasStress(f.getValue())) {
                        continue; // прапускаем формы без націска
                    }
                    forms.add(f.getValue());
                }
            }
            if (!forms.isEmpty()) {
                bw.write(p.getPdgId() + ":" + String.join(";", forms));
                bw.newLine();
                lines++;
            }
        }
    }
    IO.println("Successfully wrote " + lines + " lines to " + stressListOutput.toAbsolutePath());
}
