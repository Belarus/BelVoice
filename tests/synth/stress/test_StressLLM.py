from pathlib import Path
from unittest.mock import patch

import pytest

from belvoice.synth.stress.StressLLM import StressLLM

DICTIONARY_FILE = Path(__file__).parent / "test_upper_lower.md"


def _make_llm() -> StressLLM:
    return StressLLM(model_name="dummy", requests_file=DICTIONARY_FILE)


def test_upper_case_no_llm():
    llm = _make_llm()
    with patch.object(StressLLM, "_request_llm") as mocked_request_llm:
        result = llm.apply_stresses("Без Яны.")

    mocked_request_llm.assert_not_called()
    assert result == "Без Я́ны."


def test_lower_case_no_llm():
    llm = _make_llm()
    with patch.object(StressLLM, "_request_llm") as mocked_request_llm:
        result = llm.apply_stresses("Пайшлі яны самі.")

    mocked_request_llm.assert_not_called()
    assert result == "Пайшлі яны́ самі."


def test_upper_case_calls_llm():
    llm = _make_llm()
    with patch.object(StressLLM, "_request_llm", return_value="Я́на") as mocked_request_llm:
        result = llm.apply_stresses("Прыйшла Яна.")

    mocked_request_llm.assert_called_once()
    assert result == "Прыйшла Я́на."


def test_lower_case_calls_llm():
    llm = _make_llm()
    with patch.object(StressLLM, "_request_llm", return_value="яна́") as mocked_request_llm:
        result = llm.apply_stresses("Прыйшла яна.")

    mocked_request_llm.assert_called_once()
    assert result == "Прыйшла яна́."


def test_callback_progress():
    progress_values = []
    llm = StressLLM(model_name="dummy", requests_file=DICTIONARY_FILE, callback=progress_values.append)
    with patch.object(StressLLM, "_request_llm", return_value="Я́на"):
        result = llm.apply_stresses("Без Яны. Прыйшла Яна.")

    assert result == "Без Я́ны. Прыйшла Я́на."
    # 4 words in total: "Без", "Яны", "Прыйшла", "Яна"
    assert progress_values == [25.0, 50.0, 75.0, 100.0]


def test_callback_empty_text():
    progress_values = []
    llm = StressLLM(model_name="dummy", requests_file=DICTIONARY_FILE, callback=progress_values.append)
    result = llm.apply_stresses("")

    assert result == ""
    assert progress_values == [100.0]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
