import json
import subprocess
import re
import tempfile
import shutil
from dataclasses import dataclass
from typing import Dict, List

import pytest

# Import the functions and dataclasses from our main module.
from neuromansui.main import (
    compile_contract,
    generate_contract,
    iterative_evaluation,
    CompilationResult,
    CompilationFeedback,
)

# A simple fake CompletedProcess to simulate subprocess.run results.
class FakeCompletedProcess:
    def __init__(self, returncode: int, stderr: str):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = ""



def test_compile_contract_success(monkeypatch):
    """
    Test the success path of compile_contract.
    We simulate a successful compiler run by patching subprocess.run.
    """
    call_count = 0

    def fake_run(args, cwd, capture_output, text):
        nonlocal call_count
        call_count += 1
        # For "json-errors" call, return a dummy value (not used when success)
        if "json-errors" in args:
            return FakeCompletedProcess(0, "")
        else:
            # For primary build call, simulate a successful run.
            return FakeCompletedProcess(0, "Compilation Successful output with no errors")

    monkeypatch.setattr(subprocess, "run", fake_run)

    dummy_source = "module Dummy {}"
    result: CompilationResult = compile_contract(dummy_source)
    assert result.is_successful is True
    assert "Compilation Successful" in result.status_message
    assert result.stats["errors"] == 0
    # The verbose output should be cleaned of any ANSI codes
    assert result.feedback.verbose_output == "Compilation Successful output with no errors"


def test_compile_contract_error(monkeypatch):
    """
    Test the error path of compile_contract.
    We simulate a failed compiler run and a JSON error array for collect_errors.
    """
    # Create a dummy JSON error output.
    dummy_json = '[{"file": "dummy.move", "line": 1, "column": 1, "level": "Error", "category": 1, "code": 123, "msg": "dummy error"}]'

    def fake_run(args, cwd, capture_output, text):
        if "json-errors" in args:
            return FakeCompletedProcess(1, dummy_json)
        else:
            # Simulate a failed run with ANSI color codes.
            return FakeCompletedProcess(1, "\x1b[31mCompilation error occurred\x1b[0m")

    monkeypatch.setattr(subprocess, "run", fake_run)

    dummy_source = "module Dummy {}"
    result: CompilationResult = compile_contract(dummy_source)
    assert result.is_successful is False
    # Our dummy JSON contains one error.
    assert result.stats.get("errors", 0) == 1
    # Ensure that ANSI sequences have been stripped from the verbose output.
    assert "\x1b" not in result.feedback.verbose_output
    # Make sure the dummy error message is present in the rendered error table.
    assert "dummy error" in result.feedback.error_table


def test_generate_contract(monkeypatch):
    """
    Test generate_contract by patching the OpenAI client.
    """
    # Create a dummy response simulating the OpenAI API response.
    class DummyResponse:
        class DummyChoice:
            class DummyMessage:
                content = "dummy contract generated"
            message = DummyMessage()
        choices = [DummyChoice()]

    def fake_create(**kwargs):
        return DummyResponse()

    # Patch the OpenAI client's chat.completions.create function.
    # We use the __globals__ of generate_contract to access the client.
    monkeypatch.setattr(
        generate_contract.__globals__['client'].chat.completions, "create", fake_create
    )

    prompt = "Generate a dummy contract"
    system_prompt = "System prompt dummy"
    result = generate_contract(prompt, system_prompt)
    assert result == "dummy contract generated"


def test_iterative_evaluation(monkeypatch):
    """
    Test iterative_evaluation by overriding generate_contract and compile_contract.
    
    Simulate a scenario where the first compilation fails and the second succeeds.
    """
    # A counter to count compile_contract calls.
    call_counter = {"compile": 0}

    def dummy_generate_contract(prompt: str, system_prompt: str) -> str:
        # Always return the same dummy contract.
        return "dummy contract"

    def dummy_compile_contract(source: str) -> CompilationResult:
        call_counter["compile"] += 1
        if call_counter["compile"] == 1:
            # First iteration fails.
            feedback = CompilationFeedback(verbose_output="error")
            return CompilationResult(
                is_successful=False,
                status_message="dummy error",
                feedback=feedback,
                stats={"errors": 1, "compiler_warnings": 0, "linter_warnings": 0},
            )
        else:
            # Second iteration succeeds.
            feedback = CompilationFeedback(verbose_output="success")
            return CompilationResult(
                is_successful=True,
                status_message="dummy success",
                feedback=feedback,
                stats={"errors": 0, "compiler_warnings": 0, "linter_warnings": 0},
            )

    monkeypatch.setattr("neuromansui.main.generate_contract", dummy_generate_contract)
    monkeypatch.setattr("neuromansui.main.compile_contract", dummy_compile_contract)

    base_prompt = "base prompt"
    system_prompt = "system prompt"
    final_contract = iterative_evaluation(base_prompt, system_prompt, max_iterations=2)
    # The final contract should be our dummy generated contract.
    assert final_contract == "dummy contract"
    # We should have invoked compile_contract twice.
    assert call_counter["compile"] == 2 