"""
Архітэктура мадэлі жыве ў пакеце belvoice (framework/belvoice/synth/stress/StressML_model.py),
каб адна і тая ж рэалізацыя выкарыстоўвалася і пры навучанні, і пры інферэнсе (StressML).
Гэты файл - зручная кропка імпарту для скрыптоў навучання ў tools/stress_ml.

Патрабуе, каб пакет BelVoice быў усталяваны/бачны ў PYTHONPATH, напр.:
    pip install -e /home/alex/gits/BelVoice
"""
from belvoice.synth.stress.StressML_model import StressML_model, PAD_ID, UNK_ID, FIRST_CHAR_ID

__all__ = ["StressML_model", "PAD_ID", "UNK_ID", "FIRST_CHAR_ID"]
