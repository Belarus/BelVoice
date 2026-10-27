package org.alex73.fanetyka.impl.str;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * Клас для канвертацыі гукаў паміж тэкставым фарматам (які фармуецца ў {@link VoiceToStringTTS})
 * і байтавымі токенамі (і наадварот).
 * <p>
 * Спіс токенаў загружаецца з рэсурсу {@code token_str.txt}.
 */
public class TokenStr {
    /**
     * Адлюстраванне байтавага токена ў радковы запіс.
     */
    static final String[] token2str;
    /**
     * Прыкмета таго, ці з'яўляецца токен галосным гукам.
     */
    static final boolean[] isVowel;
    /**
     * Адлюстраванне радка токена ў байтавы ідэнтыфікатар.
     */
    static final Map<String, Byte> str2token;
    /**
     * Максімальная даўжыня радка токена.
     */
    static final int maxTokenStrLen;

    static {
        List<String> t2s = new ArrayList<>();
        Map<String, Byte> s2t = new HashMap<>();
        List<Boolean> vowels = new ArrayList<>();
        int maxLen = 0;
        try (BufferedReader rd = new BufferedReader(new InputStreamReader(TokenStr.class.getResourceAsStream("token_str.txt"), StandardCharsets.UTF_8))) {
            String s;
            while ((s = rd.readLine()) != null) {
                String token;
                boolean vowel = s.contains("[vowel]");
                s = s.replace("[vowel]", "");
                s = s.trim();
                if (s.isEmpty()) {
                    // Пусты радок адпавядае прагалу
                    s = " ";
                }
                s2t.put(s, (byte) t2s.size());
                t2s.add(s);
                vowels.add(vowel);
                maxLen = Math.max(maxLen, s.length());
            }
        } catch (Exception ex) {
            throw new ExceptionInInitializerError(ex);
        }
        token2str = t2s.toArray(new String[0]);
        str2token = Collections.unmodifiableMap(s2t);
        maxTokenStrLen = maxLen;

        boolean[] v = new boolean[vowels.size()];
        for (int i = 0; i < vowels.size(); i++) {
            v[i] = vowels.get(i);
        }
        isVowel = v;
    }

    public static boolean isVowel(byte token) {
        int idx = token & 0xFF;
        return idx < isVowel.length && isVowel[idx];
    }

    public static String token2str(byte token) {
        return token2str[token & 0xFF];
    }

    /**
     * Канвертуе радок гукаў у масіў байтавых токенаў.
     * <p>
     * Выкарыстоўвае прагны пошук найдаўжэйшага супадзення з вядомымі токенамі (даўжынёй да {@link #maxTokenStrLen}).
     *
     * @param s радок з гукамі ў фармаце TTS
     * @return масіў байтавых ідэнтыфікатараў токенаў
     * @throws IllegalArgumentException калі сустракаецца невядомы токен
     */
    public static byte[] str2tokens(String s) {
        ByteArrayOutputStream tokens = new ByteArrayOutputStream();
        int i = 0;
        while (i < s.length()) {
            boolean found = false;
            // Шукаем найдаўжэйшы вядомы токен, пачынаючы з maxTokenStrLen
            for (int len = Math.min(maxTokenStrLen, s.length() - i); len > 0; len--) {
                String sub = s.substring(i, i + len);
                Byte token = str2token.get(sub);
                if (token != null) {
                    tokens.write(token);
                    i += len;
                    found = true;
                    break;
                }
            }
            if (!found) {
                throw new IllegalArgumentException("Unknown token in string: " + s.substring(i)+" full string: "+s);
            }
        }
        return tokens.toByteArray();
    }

    /**
     * Канвертуе частку масіва байтавых токенаў назад у радок гукаў.
     *
     * @param tokens масіў байтавых токенаў
     * @param from   пачатковы індэкс (уключна)
     * @param to     канчатковы індэкс (выключна)
     * @return адноўлены радок з гукамі ў фармаце TTS
     */
    public static String tokens2str(byte[] tokens, int from, int to) {
        StringBuilder sb = new StringBuilder();
        for (int i = from; i < to; i++) {
            sb.append(token2str[tokens[i]]);
        }
        return sb.toString();
    }

    /**
     * Канвертуе масіў байтавых токенаў назад у радок гукаў.
     *
     * @param tokens масіў байтавых токенаў
     * @return адноўлены радок з гукамі ў фармаце TTS
     */
    public static String tokens2str(byte[] tokens) {
        return tokens2str(tokens, 0, tokens.length);
    }
}
