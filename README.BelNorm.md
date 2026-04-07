Belarusian Text Normalization Library
=====================================

This library provides tools for preparing Belarusian text for Text-to-Speech (TTS) applications. Key features include:

- Splitting text into sentences
- Normalizing numbers and abbreviations
- Handling common Belarusian contractions and special symbols

Designed for easy integration, this library helps ensure that text is correctly formatted and pronounced by TTS systems.

Usage example
-------------

    from BelNorm import BelSplitter, NormalizerLLM
    from BelG2P import BelG2PWrapper

    g2p=BelG2PWrapper()
    normalizer=NormalizerLLM("gemini/gemini-flash-lite-latest")
    splitter=BelSplitter()

    text="Нейкі беларускі тэкст. І прачытаць яго трэба 3 разы."
    print(f"Input text: {text}")

    for paragraph in splitter.parse([text]):
        for sentence in paragraph:
            if not sentence.is_normalized:
                print("Normalization required: "+sentence.text)
                sentence.normalize(normalizer.normalize)
                print(sentence.text)
            print(sentence.convert_tts(g2p.convert))

Do not forget to add some environment variable for LLM usage. For Gemini, it should be GEMINI_API_KEY.
