from openwhisper.cleanup.snippets import SnippetExpander
from openwhisper.settings import Snippet


def test_slash_snippet_from_spoken_slash():
    out = SnippetExpander([
        Snippet(trigger="/sig", replacement="— Felipe"),
    ]).expand("please close with slash sig")
    assert "— Felipe" in out
    assert "/sig" not in out


def test_phrase_snippet():
    out = SnippetExpander([
        Snippet(trigger="signature block", replacement="Best,\nFelipe", trigger_is_phrase=True),
    ]).expand("add the signature block here")
    assert "Best,\nFelipe" in out


def test_longest_match_wins():
    expander = SnippetExpander([
        Snippet(trigger="hi", replacement="HELLO", trigger_is_phrase=True),
        Snippet(trigger="hi there", replacement="GREETINGS", trigger_is_phrase=True),
    ])
    assert expander.expand("hi there") == "GREETINGS"


def test_no_snippets_is_noop():
    assert SnippetExpander([]).expand("hello") == "hello"


def test_slash_trigger_does_not_fire_mid_word():
    expander = SnippetExpander([Snippet(trigger="/sig", replacement="X")])
    # "/sigmoid" should not expand
    assert expander.expand("the /sigmoid curve") == "the /sigmoid curve"
