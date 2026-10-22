package org.alex73.fanetyka.impl.str;

import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class TokenStrTest {

    private static final Set<String> EXPECTED_VOWELS = Set.of(
            "а", "а´", "ɐ", "э", "э´", "і", "і´", "о", "о´", "у", "у´", "ы", "ы´", "ə", "ə´"
    );

    @Test
    void testIsVowel() {
        for (int i = 0; i < TokenStr.token2str.length; i++) {
            byte token = (byte) i;
            String tokenStr = TokenStr.token2str[i];
            boolean expected = EXPECTED_VOWELS.contains(tokenStr);
            assertEquals(expected, TokenStr.isVowel(token),
                    () -> "Unexpected isVowel result for token id " + token + ": \"" + tokenStr + "\"");
        }
    }

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
