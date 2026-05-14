import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

void main() throws Exception {
    Path dbStatOutput = Path.of("../../framework/src/stress/stresses-stat.json");
    Gson gson = new GsonBuilder().disableHtmlEscaping().create();

    Map<String, String> stressStat = new TreeMap<>();
    try (var in = this.getClass().getResourceAsStream("/amohrafy_naciski.txt"); var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
        String line;
        while ((line = reader.readLine()) != null) {
            stressStat.put(line.replace("+", ""), line.replace("+", "\u0301"));
        }
    }

    Files.writeString(dbStatOutput, gson.toJson(stressStat));
    IO.println("Successfully wrote " + stressStat.size() + " stress entries to " + dbStatOutput.toAbsolutePath());
}
