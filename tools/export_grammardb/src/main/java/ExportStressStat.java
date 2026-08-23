import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

/**
 * Чытае amohrafy_naciski.txt і стварае stresses-stat.json з статыстычным спісам амографаў для зняццця аманіміі праз StressStat.py.
 */
void main() throws Exception {
    Path dbStatOutput = Path.of("../../framework/belvoice/synth/stress/stresses-stat.json");
    Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

    Map<String, String> stressStat = new TreeMap<>(Collator.getInstance(Locale.of("be")));
    try (var in = this.getClass().getResourceAsStream("/amohrafy_naciski_stat.txt"); var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
        String line;
        while ((line = reader.readLine()) != null) {
            if (stressStat.put(line.replace("+", ""), line.replace("+", "\u0301")) != null) {
                throw new Exception("Duplicate entry in amohrafy_naciski.txt: " + line);
            }
        }
    }

    Files.writeString(dbStatOutput, gson.toJson(stressStat));
    IO.println("Successfully wrote " + stressStat.size() + " stress entries to " + dbStatOutput.toAbsolutePath());
}
