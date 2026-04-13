from openwhisper.cleanup.heuristic import HeuristicCleanup
from openwhisper.settings import DictationMode


def test_removes_fillers_in_polished_mode():
    out = HeuristicCleanup().apply("um hello uh world", DictationMode.polished)
    lowered = out.text.lower()
    assert " um " not in lowered
    assert " uh " not in lowered


def test_keeps_fillers_in_verbatim():
    out = HeuristicCleanup().apply("um hello uh world", DictationMode.verbatim)
    assert "um" in out.text.lower()


def test_capitalizes_and_terminates():
    out = HeuristicCleanup().apply("hello world", DictationMode.polished)
    assert out.text.startswith("Hello")
    assert out.text.endswith(".")


def test_spoken_punctuation():
    out = HeuristicCleanup().apply("hello comma world period", DictationMode.polished)
    assert "," in out.text
    assert out.text.endswith(".")


def test_looks_clean_skip_list():
    out = HeuristicCleanup().apply(
        "The quick brown fox jumps over the lazy dog.", DictationMode.verbatim
    )
    assert out.looks_clean is True


def test_looks_clean_fails_for_long_text():
    long_text = ("word " * 60) + "."
    out = HeuristicCleanup().apply(long_text, DictationMode.verbatim)
    assert out.looks_clean is False


def test_empty_input_safe():
    out = HeuristicCleanup().apply("", DictationMode.polished)
    assert out.text == ""
    assert out.looks_clean is True
