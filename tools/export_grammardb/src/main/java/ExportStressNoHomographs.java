import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

/**
 * Чытае граматычную базу і стварае stresses-nohomographs.json з спісам націскаў, для якіх няма аманіміі.
 */
void main() throws Exception {
    Map<String, Set<String>> stressMap = new HashMap<>();
    Path dbOutput = Path.of("../../framework/belvoice/synth/stress/stresses-nohomographs.json");
    Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

    GrammarDBStressReader reader = new GrammarDBStressReader("/home/alex/gits/GrammarDB/data");
    Map<String, String> singleStressMap = reader.getNoHomographs();

    IO.println("Sorting...");
    Map<String, String> sortedSingleStressMap = new TreeMap<>(Collator.getInstance(Locale.of("be")));
    sortedSingleStressMap.putAll(singleStressMap);

    IO.println("Writing...");
    Files.writeString(dbOutput, gson.toJson(sortedSingleStressMap));
    IO.println("Successfully wrote " + sortedSingleStressMap.size() + " stress entries to " + dbOutput.toAbsolutePath());
}
