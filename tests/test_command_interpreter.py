from openwhisper.commands.command import DictationCommand
from openwhisper.commands.interpreter import RegexCommandInterpreter


def test_pure_command_has_high_confidence():
    d = RegexCommandInterpreter().interpret("new line")
    assert d.command == DictationCommand.new_line.value
    assert d.confidence > 0.9
    assert d.residual_text == ""


def test_new_paragraph_beats_new_line():
    assert RegexCommandInterpreter().interpret("new paragraph").command == DictationCommand.new_paragraph.value


def test_rewrite_professional():
    assert RegexCommandInterpreter().interpret("rewrite professionally").command == DictationCommand.rewrite_professional.value


def test_undo_last():
    assert RegexCommandInterpreter().interpret("undo last dictation").command == DictationCommand.undo_last_dictation.value


def test_mixed_utterance_lowers_confidence():
    d = RegexCommandInterpreter().interpret("hello there send it")
    assert d.command == DictationCommand.send.value
    assert d.confidence < 0.9
    assert d.residual_text == "hello there"


def test_non_command_returns_none():
    d = RegexCommandInterpreter().interpret("the quick brown fox")
    assert d.command is None


def test_bulleted_and_bullet_both_match():
    assert RegexCommandInterpreter().interpret("bullet list").command == DictationCommand.bullet_list.value
    assert RegexCommandInterpreter().interpret("bulleted list").command == DictationCommand.bullet_list.value


def test_press_keys():
    ci = RegexCommandInterpreter()
    assert ci.interpret("press enter").command == DictationCommand.press_enter.value
    assert ci.interpret("press tab").command == DictationCommand.press_tab.value
    assert ci.interpret("press escape").command == DictationCommand.press_escape.value


def test_destructive_flag():
    assert DictationCommand.send.is_destructive
    assert DictationCommand.press_enter.is_destructive
    assert not DictationCommand.new_line.is_destructive
