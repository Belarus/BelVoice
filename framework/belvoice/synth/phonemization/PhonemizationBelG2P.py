import jpype
import jpype.imports
from jpype.types import *
import os
import pooch

def start_jvm():
    if jpype.isJVMStarted():
        return

    jar_path = os.environ.get("PHONEMIZATION_BELG2P_JAR")
    if not jar_path:
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
        self.finder = GrammarFinder(db)

    def convert(self, text: str):
        from org.alex73.fanetyka.impl import Fanetyka3, FanetykaText
        from java.util import ArrayList

        ft = FanetykaText(self.finder, text)
        return ft.ipa2tts
