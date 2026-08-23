import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Чытае Тлумачальны слоўнік з https://github.com/verbumby/slouniki/raw/refs/heads/main/tsbm/tsbm.html
 */
public class ParseTlum {
    void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("Памылка: не пазначаны шлях да файла.");
            System.err.println("Выкарыстанне: java ParseTlum <шлях_да_файла>");
            System.exit(1);
        }
        new ParseTlum().getArticles(args[0]);
    }

    Map<String, List<String>> getArticles(String fn) throws Exception {
        String content = Files.readString(Path.of(fn));

        Map<String, String> replacements = readGroupsFromResources("tsbm_replaces.html");
        for (Map.Entry<String, String> entry : replacements.entrySet()) {
            content = content.replace(entry.getKey(), entry.getValue());
        }

        Map<String, List<String>> result = new HashMap<>();

        Document doc = Jsoup.parse(content);

        // Знаходзім усе пачаткі артыкулаў (загалоўныя словы)
        Elements articles = doc.select("p.ms-0");
        for (Element articleStart : articles) {
            // Выцягваем само слова
            Elements hwTags = articleStart.select("strong.hw");
            if (hwTags.isEmpty())
                throw new Exception("Не знойдзены тэг <strong class=\"hw\"> у артыкуле, які пачынаецца з: " + articleStart.text());

            List<String> words = hwTags.stream().map(Element::text).toList();
            int wordIndex = 1;
            for (Element supTag : articleStart.select("sup")) {
                Element p = supTag.parent();
                boolean isBrown = false;
                while (p != null && p != articleStart) {
                    if (p.tagName().equals("span") && p.attr("style").contains("brown")) {
                        isBrown = true;
                        break;
                    }
                    p = p.parent();
                }
                if (!isBrown) {
                    wordIndex = Integer.parseInt(supTag.text().trim());
                    break;
                }
            }

            //System.out.println("\n--- Словы: " + String.join(", ", words) + " " + wordIndex + " ---");
            String o = "";

            // Бяром наступны элемент пасля <p class="ms-0">
            Element currentSibling = articleStart.nextElementSibling();

            boolean inIdioms = false;
            // Перабіраем усе блокі, пакуль гэта параграф з класам ms-2
            while (currentSibling != null && currentSibling.tagName().equals("p") && currentSibling.hasClass("ms-2")) {
                // Праверка на маркер пачатку фразеалагізмаў
                if (currentSibling.text().trim().equals("•••")) {
                    inIdioms = true;
                    currentSibling = currentSibling.nextElementSibling();
                    o += "\nФразеалагізмы:\n";
                    continue;
                }

                if (inIdioms) {
                    String text = "  - " + currentSibling.text().trim() + "\n";
                    o += text;
                    currentSibling = currentSibling.nextElementSibling();
                    continue;
                }

                // 1. Дастаем УСЕ прыклады ў гэтым абзацы
                Elements examples = currentSibling.select("v-ex");

                // 2. Дастаем тлумачэнне
                // Робім копію вузла (clone), каб метад remove() не знішчыў дадзеныя ў самім дакуменце
                Element clone = currentSibling.clone();

                // Перад выдаленнем v-abbr, заменім маркеры на тэкст, які застанецца
                for (Element abbr : clone.select("v-abbr")) {
                    String t = abbr.text().trim();
                    if (t.equals("//") || t.equals("/")) {
                        abbr.before(" " + t + " ");
                    }
                }

                // Выдаляем з копіі прыклады, аўтараў (<i>) і скароты (<v-abbr>)
                clone.select("v-ex, i, v-abbr").remove();

                // Атрымліваем тэкст і прыбіраем лішнія прабелы і знакі пунктуацыі па краях
                String text = clone.text().trim();
                boolean hasNumber = text.matches("^\\d+\\..*");

                if (!text.isEmpty()) {
                    String prefix = hasNumber ? "\nЗначэнне " : "\nЗначэнне: ";
                    o +=  text;
                }

                if (!examples.isEmpty()) {
                    o += "\n\nПрыклады:\n";
                    for (Element ex : examples) {
                        for (String e : ex.text().split("□")) {
                            o += "  - " + e.trim() + "\n";
                        }
                    }
                }

                // Пераходзім да наступнага абзаца значэння
                currentSibling = currentSibling.nextElementSibling();
            }
            //System.out.println(o);

            if (o.trim().matches("Значэнне: \\S+(\\s*[0-9]?)\\.")) {
                // толькі спасылка на іншае слова
                continue;
            }
            if (words.size() > 1 && wordIndex != 1) {
               // throw new Exception("Няправільны індэкс для некалькіх слоў: знойдзены " + wordIndex + ", але ёсць " + words.size() + " слоў");
            }
            for (String word : words) {
                List<String> wordsList = result.computeIfAbsent(word, k -> new ArrayList<>());
                if (wordsList.size() != wordIndex - 1) {
                  //  throw new Exception("Няправільны індэкс у слове " + word + ": знойдзены " + wordIndex + ", але ўжо ёсць " + wordsList.size());
                }
                wordsList.add(o);
            }
        }
        return result;
    }

    private Map<String, String> readGroupsFromResources(String fileName) throws Exception {
        try (InputStream is = ParseTlum.class.getClassLoader().getResourceAsStream(fileName)) {
            if (is == null) {
                throw new Exception("Файл не знойдзены ў рэсурсах: " + fileName);
            }

            String content = new String(is.readAllBytes(), StandardCharsets.UTF_8);
            Map<String, String> result = new LinkedHashMap<>();

            int start = 0;
            while ((start = content.indexOf('[', start)) != -1) {
                int mid = content.indexOf('|', start);
                if (mid == -1) break;

                int end = content.indexOf(']', mid);
                if (end == -1) break;

                String key = content.substring(start + 1, mid).trim();
                String value = content.substring(mid + 1, end).trim();
                result.put(key, value);

                start = end + 1;
            }

            return result;
        }
    }
}