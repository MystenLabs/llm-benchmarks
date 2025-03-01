import json
import subprocess
import re
import tempfile
import shutil
from dataclasses import dataclass
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

# Import the functions and dataclasses from our main module.
from gymnasuium.main import (
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
    # Track how many times collect_errors is called
    collect_errors_calls = 0
    
    # Create a dummy JSON error output that will be successfully parsed
    dummy_json = """
    [
      {
        "file": "dummy.move",
        "line": 1,
        "column": 1,
        "level": "Error",
        "category": 1,
        "code": 123,
        "msg": "dummy error"
      }
    ]
    """

    def fake_run(args, cwd, capture_output, text):
        if "--json-errors" in args:
            return FakeCompletedProcess(1, dummy_json)
        else:
            # Simulate a failed run with plain text (no ANSI codes)
            return FakeCompletedProcess(1, "Compilation error occurred")

    # Create a mock collect_errors function
    def mock_collect_errors(output_str):
        nonlocal collect_errors_calls
        collect_errors_calls += 1
        return {
            "E123001": [
                {
                    "file": "dummy.move", 
                    "line": 1, 
                    "column": 1, 
                    "level": "Error", 
                    "category": 1, 
                    "code": 123, 
                    "msg": "dummy error"
                }
            ]
        }

    # Also mock the strip_ansi function to make sure it's used
    def mock_strip_ansi(text):
        return text.replace("\x1b[31m", "").replace("\x1b[0m", "")

    # Replace the real functions with our mocks
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("gymnasuium.main.collect_errors", mock_collect_errors)
    monkeypatch.setattr("gymnasuium.main.strip_ansi", mock_strip_ansi)

    # Run the compile function
    dummy_source = "module Dummy {}"
    result = compile_contract(dummy_source)
    
    # Verify our mock was called
    assert collect_errors_calls == 1
    
    # Verify the result
    assert result.is_successful is False
    assert "errors" in result.stats
    assert result.stats["errors"] > 0
    assert "Compilation error occurred" in result.feedback.verbose_output
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
    result, history = generate_contract(prompt, system_prompt)
    assert result == "dummy contract generated"
    assert len(history) == 3  # system, user, assistant messages
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[2]["role"] == "assistant"


def test_iterative_evaluation(monkeypatch):
    """
    Test iterative_evaluation by overriding generate_contract and compile_contract.
    
    Simulate a scenario where the first compilation fails and the second succeeds.
    """
    # A counter to count compile_contract calls.
    call_counter = {"compile": 0}

    def dummy_generate_contract(prompt: str, system_prompt: str, message_history: list = None) -> tuple[str, list]:
        # Always return the same dummy contract and maintain history
        if message_history is None:
            message_history = [{"role": "system", "content": system_prompt}]
        message_history.append({"role": "user", "content": prompt})
        message_history.append({"role": "assistant", "content": "dummy contract"})
        return "dummy contract", message_history

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

    monkeypatch.setattr("gymnasuium.main.generate_contract", dummy_generate_contract)
    monkeypatch.setattr("gymnasuium.main.compile_contract", dummy_compile_contract)

    base_prompt = "base prompt"
    system_prompt = "system prompt"
    final_contract, fine_tuning_data = iterative_evaluation(base_prompt, system_prompt, max_iterations=2)
    # The final contract should be our dummy generated contract.
    assert final_contract == "dummy contract"
    # We should have invoked compile_contract twice.
    assert call_counter["compile"] == 2


def test_main_dark_mode_visualization(monkeypatch):
    """Test that the dark_mode argument is correctly passed to save_fine_tuning_data."""
    # Mock dependencies
    class MockPromptLoader:
        def get_prompt(self, *args, **kwargs):
            return ("test prompt", "test system prompt")
        def get_prompt_description(self, *args, **kwargs):
            return "Test description"
    
    monkeypatch.setattr('gymnasuium.main.PromptLoader', lambda *args, **kwargs: MockPromptLoader())
    
    # Mock iterative_evaluation
    monkeypatch.setattr('gymnasuium.main.iterative_evaluation', lambda *args, **kwargs: ("final contract", ["iteration data"]))
    
    # Mock save_fine_tuning_data
    mock_save_data_calls = []
    def mock_save_fine_tuning_data(data, path, dark_mode=False):
        mock_save_data_calls.append({"data": data, "path": path, "dark_mode": dark_mode})
    
    monkeypatch.setattr('gymnasuium.main.save_fine_tuning_data', mock_save_fine_tuning_data)
    
    # Mock all file operations
    monkeypatch.setattr('os.path.exists', lambda path: False)
    monkeypatch.setattr('os.makedirs', lambda *args, **kwargs: None)
    
    # Mock open to avoid file operations
    mock_file = MagicMock()
    mock_file.__enter__.return_value = mock_file
    monkeypatch.setattr('builtins.open', lambda *args, **kwargs: mock_file)
    
    # Mock input to avoid user prompts
    monkeypatch.setattr('builtins.input', lambda prompt: 'y')
    
    # Set up command line arguments - using simpler arguments that don't require as many mocks
    monkeypatch.setattr('sys.argv', [
        'main.py',
        '--prompt', 'test.prompt',
        '--module-name', 'TestModule',
        '--save-dir', '/tmp',
        '--save-iterations',
        '--dark-mode'
    ])
    
    # Run main
    from gymnasuium.main import main
    main()
    
    # Check that save_fine_tuning_data was called with dark_mode=True
    assert len(mock_save_data_calls) > 0, "save_fine_tuning_data was not called"
    assert mock_save_data_calls[0]['dark_mode'] is True 