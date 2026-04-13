from openwhisper.cleanup.dictionary import PersonalDictionary
from openwhisper.settings import DictionaryEntry


def test_alias_replaced_at_word_boundary():
    dict_ = PersonalDictionary([
        DictionaryEntry(term="OpenWhisper", aliases=["kp whisper", "kay pee whisper"]),
    ])
    assert "OpenWhisper" in dict_.apply("I use kp whisper every day")


def test_does_not_match_inside_word():
    dict_ = PersonalDictionary([
        DictionaryEntry(term="Sam", aliases=["sam"]),
    ])
    assert dict_.apply("samsung phones") == "samsung phones"


def test_case_insensitive_default():
    dict_ = PersonalDictionary([
        DictionaryEntry(term="Anthropic", aliases=["anthropic"]),
    ])
    out = dict_.apply("i love Anthropic and anthropic")
    assert out.count("Anthropic") == 2


def test_stt_hints():
    dict_ = PersonalDictionary([
        DictionaryEntry(term="Claude", aliases=["clawd"]),
    ])
    hints = dict_.stt_hints()
    assert "Claude" in hints
    assert "clawd" in hints


def test_empty_dictionary_is_noop():
    assert PersonalDictionary([]).apply("hello") == "hello"
