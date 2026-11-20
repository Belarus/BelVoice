package org.alex73.fanetyka.impl.str;

import org.alex73.fanetyka.impl.Huk;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TokenStrTest {

    // Правярае, што isVowel правільна вызначае галосныя гукі для ўсіх токенаў з token2str
    @Test
    void testIsVowel() {
        for (boolean stress : List.of(true, false)) {
            for (Huk.BAZAVY_HUK b : Huk.halosnyja) {
                Huk h = new Huk("", b);
                h.stress = stress;
                String hukStr = new ToStringSimpleStressIPA().huk2str(h);
                byte[] tokens = TokenStr.str2tokens(hukStr);
                assertEquals(1, tokens.length, "Expected single token for Huk: " + hukStr);
                assertTrue(TokenStr.isVowel(tokens[0]), "Unexpected vowel in Huk.halosnyja: " + hukStr);
            }
        }
    }

    // Правярае, што ўсе гукі маюць адпаведныя токены ў token2str і str2tokens
    @Test
    void testConvert() {
        for (Huk.POUNY_HUK ph : Huk.POUNY_HUK.values()) {
            String h = ToStringSimpleStressIPA.IPA_MAP.get(ph);
            byte[] tokens = TokenStr.str2tokens(h);
            assertEquals(1, tokens.length, "Expected single token for Huk: " + h);
        }
    }

    // Правярае зваротнае пераўтварэнне (токен -> радок -> токен) для кожнага асобнага токена
    @Test
    void testSingleTokensRoundTrip() {
        for (int i = 0; i < TokenStr.token2str.length; i++) {
            byte token = (byte) i;
            byte[] original = new byte[]{token};

            String str = TokenStr.tokens2str(original);
            assertEquals(TokenStr.token2str[i], str);

            byte[] parsed = TokenStr.str2tokens(str);
            assertArrayEquals(original, parsed,
                    () -> "Failed for token id " + token + ": \"" + TokenStr.token2str[token] + "\"");
        }
    }

    // Правярае зваротнае пераўтварэнне (токены -> радок -> токены) для ўсіх камбінацый з трох токенаў
    @Test
    void testTokenPairsRoundTrip() {
        for (int i = 0; i < TokenStr.token2str.length; i++) {
            byte t1 = (byte) i;
            for (int j = 0; j < TokenStr.token2str.length; j++) {
                byte t2 = (byte) j;
                for (int k = 0; k < TokenStr.token2str.length; k++) {
                    byte t3 = (byte) k;
                    byte[] original = new byte[]{t1, t2, t3};

                    String str = TokenStr.tokens2str(original);
                    byte[] parsed = TokenStr.str2tokens(str);

                    assertArrayEquals(original, parsed,
                            () -> "Failed for pair [" + TokenStr.token2str[t1] + "] + [" + TokenStr.token2str[t2] + "] + [" + TokenStr.token2str[t3] + "] -> \"" + str + "\"");
                }
            }
        }
    }
}
