import jpype
import jpype.imports
from jpype.types import *
import os
import pooch

def start_jvm():
    if jpype.isJVMStarted():
        return

    jar_path = pooch.retrieve(
        url="https://github.com/Belarus/BelG2P/releases/download/1.0.0/linguistics.BelG2P-1.0.0-jar-with-dependencies.jar",
        known_hash=None, # Можна дадаць хэш для праверкі цэласнасці
    )

    # Запускаем JVM
    jpype.startJVM(
        classpath=[jar_path],
        convertStrings=True
    )


class PhonemizationBelG2P:
    def __init__(self):
        start_jvm()

        from org.alex73.fanetyka.impl import FanetykaConfig
        from org.alex73.grammardb import GrammarDB2
        from org.alex73.grammardb import GrammarFinder
        from org.alex73.fanetyka.impl.str import ToStringIPA2TTS

        db = GrammarDB2.initializeFromJar();
        finder = GrammarFinder(db)
        self.config = FanetykaConfig(finder)
        self.outType = ToStringIPA2TTS()

    def convert(self, words: str):
        from org.alex73.fanetyka.impl import Fanetyka3
        from java.util import ArrayList

        f = Fanetyka3(self.config)
        jwords = ArrayList(words.split())
        f.calcFanetyka(jwords)
        return f.toString(self.outType)
