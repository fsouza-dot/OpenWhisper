"""Orchestration tests. Verify the skip-LLM heuristic, command fast-path,
dictionary/snippet application, and graceful offline mode.

We pass in a fake LLM provider so no network calls are made.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from openwhisper.cleanup.pipeline import CleanupPipeline
from openwhisper.commands.command import DictationCommand
from openwhisper.protocols import CleanupInput, CleanupResult
from openwhisper.settings import AppSettings, DictationMode, DictionaryEntry, Snippet


@dataclass
class SpyLLM:
    identifier: str = "spy"
    response: CleanupResult = field(default_factory=lambda: CleanupResult(
        cleaned="LLM OUTPUT", confidence=0.9, used_llm=True, model_used="spy"
    ))
    calls: List[CleanupInput] = field(default_factory=list)

    def clean(self, input: CleanupInput) -> CleanupResult:
        self.calls.append(input)
        return self.response


def test_skips_llm_when_verbatim_and_clean():
    spy = SpyLLM()
    pipe = CleanupPipeline(llm_provider=spy)
    settings = AppSettings.default()
    settings.dictation_mode = DictationMode.verbatim
    result = pipe.run("The quick brown fox jumps over the lazy dog.", settings)
    assert len(spy.calls) == 0
    assert result.used_llm is False


def test_pure_command_skips_llm():
    spy = SpyLLM()
    pipe = CleanupPipeline(llm_provider=spy)
    result = pipe.run("new line", AppSettings.default())
    assert len(spy.calls) == 0
    assert result.command == DictationCommand.new_line.value


def test_calls_llm_for_polished_mode():
    spy = SpyLLM()
    pipe = CleanupPipeline(llm_provider=spy)
    settings = AppSettings.default()
    settings.dictation_mode = DictationMode.polished
    pipe.run("um so i was thinking", settings)
    assert len(spy.calls) == 1


def test_applies_dictionary_before_llm():
    settings = AppSettings.default()
    settings.dictation_mode = DictationMode.verbatim
    settings.dictionary = [
        DictionaryEntry(term="OpenWhisper", aliases=["kp whisper"]),
    ]
    pipe = CleanupPipeline(llm_provider=None)
    result = pipe.run("kp whisper is great.", settings)
    assert "OpenWhisper" in result.cleaned


def test_snippet_expansion():
    settings = AppSettings.default()
    settings.dictation_mode = DictationMode.verbatim
    settings.snippets = [Snippet(trigger="/sig", replacement="- F")]
    pipe = CleanupPipeline(llm_provider=None)
    result = pipe.run("end with slash sig.", settings)
    assert "- F" in result.cleaned


def test_falls_back_gracefully_when_no_llm():
    pipe = CleanupPipeline(llm_provider=None)
    settings = AppSettings.default()
    settings.dictation_mode = DictationMode.polished
    result = pipe.run("um hello", settings)
    assert result.used_llm is False
    assert result.cleaned  # still produced something local


def test_llm_exception_falls_back_to_heuristic():
    class ErrLLM:
        identifier = "err"

        def clean(self, _input):
            raise RuntimeError("boom")

    pipe = CleanupPipeline(llm_provider=ErrLLM())
    settings = AppSettings.default()
    settings.dictation_mode = DictationMode.polished
    result = pipe.run("hello world", settings)
    assert result.used_llm is False
    assert result.cleaned
