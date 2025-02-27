"""
Main application module for Neuromansui.

This module provides functionality for compiling and iterative evaluation of 
Sui Move smart contracts using LLM-generated code.
"""

import os
import subprocess
import time
import argparse
import tempfile
import json
import shutil
import re
from io import StringIO
from dataclasses import dataclass
from typing import Optional, Dict
from dotenv import load_dotenv
import openai
from neuromansui.prompt_loader import PromptLoader, collect_errors

# Import rich for pretty printing
from rich.console import Console
from rich.table import Table
import re
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

def strip_ansi(text: str) -> str:
    """
    Remove ANSI escape sequences from the given text.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)

load_dotenv()
client = openai.OpenAI()

# Create a global console instance
console = Console()


@dataclass
class CompilationFeedback:
    """
    Structured feedback produced by the compiler.

    Attributes:
        verbose_output: The full raw output (stderr) from the compiler.
        error_table: The rendered plain text table with grouped error details.
        summary_table: A plain text table with overall error/warning counts.
        spans_table: (Optional) A table showing flagged text spans extracted from error messages.
    """
    verbose_output: str
    error_table: Optional[str] = None
    summary_table: Optional[str] = None
    spans_table: Optional[str] = None

    def __str__(self) -> str:
        parts = [f"Verbose Compiler Output:\n{self.verbose_output}"]
        if self.error_table:
            parts.append(f"\nError Details Table:\n{self.error_table}")
        if self.summary_table:
            parts.append(f"\nSummary Statistics:\n{self.summary_table}")
        if self.spans_table:
            parts.append(f"\nFlagged Text Spans:\n{self.spans_table}")
        return "\n".join(parts)


@dataclass
class CompilationResult:
    """
    Encapsulates the result of a contract compilation.

    Attributes:
        is_successful: True if the contract compiled successfully.
        status_message: A human-friendly status message.
        feedback: Detailed, structured feedback from the compilation process.
        stats: A dictionary with summary counts for errors, compiler warnings, and linter warnings.
    """
    is_successful: bool
    status_message: str
    feedback: CompilationFeedback
    stats: Dict[str, int]


def compile_contract(contract_source: str) -> CompilationResult:
    """
    Compiles a Sui Move contract using the Sui CLI.

    Args:
        contract_source: Source code of the contract to compile

    Returns:
        A CompilationResult object containing:
         - is_successful: Compilation success flag
         - status_message: A friendly message indicating success or failure
         - feedback: Structured feedback (verbose output, error details, statistics)
         - stats: Summary statistics (total errors, compiler warnings, linter warnings)
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # Write a basic Move.toml file
        move_toml = """
[package]
name = "TempContract"
version = "0.0.1"

[dependencies]
Sui = { git = "https://github.com/MystenLabs/sui.git", subdir = "crates/sui-framework/packages/sui-framework", rev = "framework/testnet" }

[addresses]
temp_addr = "0x0"
"""
        with open(os.path.join(temp_dir, "Move.toml"), "w") as f:
            f.write(move_toml)

        # Create sources directory and write the contract code
        sources_dir = os.path.join(temp_dir, "sources")
        os.makedirs(sources_dir, exist_ok=True)
        with open(os.path.join(sources_dir, "temp_contract.move"), "w") as f:
            f.write(contract_source)

        # Run the compiler with verbose output
        verbose_result = subprocess.run(
            ["sui", "move", "build", "--lint", "--doc", "--generate-struct-layouts"],
            cwd=temp_dir,
            capture_output=True,
            
            text=True,
        )

        # Run the compiler with JSON errors output (sent to stderr)
        json_result = subprocess.run(
            ["sui", "move", "build", "--json-errors"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )

        verbose_output = verbose_result.stderr

        if verbose_result.returncode == 0:
            feedback = CompilationFeedback(verbose_output=verbose_output)
            return CompilationResult(
                is_successful=True,
                status_message="[bold green]Compilation Successful! ✅[/bold green]",
                feedback=feedback,
                stats={"errors": 0, "compiler_warnings": 0, "linter_warnings": 0},
            )
        else:
            try:
                grouped_errors = collect_errors(json_result.stderr)

            except ValueError as e:
                feedback = CompilationFeedback(
                    verbose_output=verbose_output
                )
                return CompilationResult(
                    is_successful=False,
                    status_message="[bold red]Compilation Error! ❌[/bold red]",
                    feedback=CompilationFeedback(
                        verbose_output=f"Error extracting error details: {e}\nVerbose Output:\n" + strip_ansi(verbose_output)
                    ),
                    stats={},
                )

            # Build a rich table for error details
            error_table = Table(title="Compilation Error Summary", show_lines=True)
            error_table.add_column("Error Code", style="bold cyan", justify="center")
            error_table.add_column("Occurrences", style="bold yellow", justify="center")
            error_table.add_column("Level", style="green", justify="center")
            error_table.add_column("Sample Message", style="magenta")

            total_errors = 0
            total_compiler_warnings = 0
            total_linter_warnings = 0

            for code, errors in grouped_errors.items():
                sample_error = errors[0]
                level = sample_error.get("level", "Unknown")
                count = len(errors)
                total_errors += count
                if level.lower().startswith("warn"):
                    total_compiler_warnings += count  # Extend logic if linter warnings differ.
                error_table.add_row(f"🚨 {code}", str(count), level, sample_error.get("msg", ""))

            # Capture rendered error table as plain text (without ANSI codes)
            capture_console = Console(record=True, width=120)
            capture_console.print(error_table)
            error_table_text = capture_console.export_text(styles=False)

            # Build a summary table for overall statistics
            summary_table = Table(show_header=False, box=None)
            summary_table.add_row("  Total Errors:", f"[bold red]{total_errors}[/bold red]")
            summary_table.add_row("  Total Compiler Warnings:", f"[bold yellow]{total_compiler_warnings}[/bold yellow]")
            summary_table.add_row("  Total Linter Warnings:", f"[bold blue]{total_linter_warnings}[/bold blue]")
            capture_console = Console(record=True, width=120)
            capture_console.print(summary_table)
            summary_table_text = capture_console.export_text(styles=False)

            # Extract flagged text spans from error messages (for example, text between quotes or backticks)
            span_pattern = re.compile(r"[`'\"]([\w\d_]+)[`'\"]")
            span_counts = {}
            for errors in grouped_errors.values():
                for err in errors:
                    msg = err.get("msg", "")
                    spans = span_pattern.findall(msg)
                    for span in spans:
                        span_counts[span] = span_counts.get(span, 0) + 1

            spans_table_text = None
            if span_counts:
                spans_table = Table(title="Flagged Text Spans", show_lines=True)
                spans_table.add_column("Span", style="bold cyan", justify="center")
                spans_table.add_column("Occurrences", style="bold yellow", justify="center")
                for span, count in span_counts.items():
                    spans_table.add_row(span, str(count))
                capture_console = Console(record=True, width=80)
                capture_console.print(spans_table)
                spans_table_text = capture_console.export_text(styles=False)

            feedback = CompilationFeedback(
                verbose_output=verbose_output,
                error_table=error_table_text,
                summary_table=summary_table_text,
                spans_table=spans_table_text
            )

            return CompilationResult(
                is_successful=False,
                status_message="[bold red]Compilation Error! ❌[/bold red]",
                feedback=feedback,
                stats={
                    "errors": total_errors,
                    "compiler_warnings": total_compiler_warnings,
                    "linter_warnings": total_linter_warnings,
                },
            )
    finally:
        shutil.rmtree(temp_dir)


def generate_contract(prompt: str, system_prompt: str = "You are an expert in Sui Move smart contract development.") -> str:
    """
    Use OpenAI API to generate contract code.
    
    Args:
        prompt: The prompt to send to the model
        system_prompt: The system prompt to set the model's behavior
        
    Returns:
        Generated contract source code
    """
    console.print("[bold green]🛠️ Requesting contract generation from OpenAI...[/bold green]")
    console.print("[italic]Prompt being sent to the model:[/italic]")
    console.print(f"[dim]{prompt}[/dim]")
    with console.status("[bold blue]Awaiting OpenAI response...[/bold blue]", spinner="dots"):
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
    generated = response.choices[0].message.content
    console.print("[bold green]✅ Contract generation successful![/bold green]")
    return generated


def iterative_evaluation(base_prompt: str, system_prompt: str = None, max_iterations: int = 5) -> str:
    """
    Iteratively calls the LLM to refine the contract source code.
    
    Args:
        base_prompt: The base prompt to use for generation
        system_prompt: The system prompt to set the model's behavior
        max_iterations: Maximum number of iterations to perform
        
    Returns:
        Final contract source code
    """
    previous_stats = None
    feedback_text = "Initial run"
    contract_source = ""
    
    # Metrics to track
    iterations_history = []

    if system_prompt is None:
        system_prompt = "You are an expert in Sui Move smart contract development."

    # Create a progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Refining contract...", total=max_iterations)
        
        for i in range(max_iterations):
            console.print(f"\n[bold yellow]=== Iteration {i+1}/{max_iterations} ===[/bold yellow]")
            full_prompt = base_prompt if i == 0 else f"{base_prompt}\n\nFeedback: {feedback_text}"
            contract_source = generate_contract(full_prompt, system_prompt)
            
            console.print("[bold cyan]Generated contract source:[/bold cyan]")
            console.print(contract_source)

            compiled_result = compile_contract(contract_source)
            console.print("[bold magenta]Compiler Feedback:[/bold magenta]")
            console.print(compiled_result.status_message, highlight=False, markup=True)

            # Update iteration metrics
            iteration_metrics = {
                "iteration": i+1,
                "errors": compiled_result.stats.get("errors", 0),
                "compiler_warnings": compiled_result.stats.get("compiler_warnings", 0),
                "linter_warnings": compiled_result.stats.get("linter_warnings", 0),
                "success": compiled_result.is_successful
            }
            iterations_history.append(iteration_metrics)

            delta_str = ""
            if previous_stats is not None and compiled_result.stats:
                delta_errors = compiled_result.stats.get("errors", 0) - previous_stats.get("errors", 0)
                delta_compiler = compiled_result.stats.get("compiler_warnings", 0) - previous_stats.get("compiler_warnings", 0)
                delta_linter = compiled_result.stats.get("linter_warnings", 0) - previous_stats.get("linter_warnings", 0)
                delta_str = (
                    f"[bold]Delta Changes:[/bold] Errors: [red]{delta_errors:+d}[/red] | "
                    f"Compiler Warnings: [yellow]{delta_compiler:+d}[/yellow] | "
                    f"Linter Warnings: [blue]{delta_linter:+d}[/blue]"
                )
                console.print(delta_str)
            previous_stats = compiled_result.stats

            # Update progress
            progress.update(task, advance=1, description=f"[cyan]Iteration {i+1}/{max_iterations}")
            
            if compiled_result.is_successful:
                console.print("[bold green]Contract compiled successfully![/bold green]")
                break
            else:
                feedback_text = (
                    f"The contract did not compile.\n\n{strip_ansi(compiled_result.feedback.verbose_output)}\n"
                )
                if delta_str:
                    feedback_text += delta_str + "\n"
                feedback_text += "Please revise the contract accordingly, ensuring that all issues are resolved."
                time.sleep(1)
    
    # Print summary metrics
    if iterations_history:
        console.print("\n[bold blue]== Refinement Summary ==[/bold blue]")
        
        # Create a summary table
        summary_table = Table(title="Refinement Metrics")
        summary_table.add_column("Iteration", style="cyan")
        summary_table.add_column("Errors", style="red")
        summary_table.add_column("Warnings", style="yellow")
        summary_table.add_column("Status", style="green")
        
        for metrics in iterations_history:
            status = "[green]Success" if metrics["success"] else "[red]Failed"
            summary_table.add_row(
                str(metrics["iteration"]),
                str(metrics["errors"]),
                str(metrics["compiler_warnings"] + metrics["linter_warnings"]),
                status
            )
        
        console.print(summary_table)

    return contract_source


def list_available_prompts(prompt_loader: PromptLoader) -> None:
    """
    List all available prompts with descriptions.
    
    Args:
        prompt_loader: The prompt loader instance
    """
    console.print("[bold underline]Available prompts:[/bold underline]")
    for prompt_path in prompt_loader.list_prompts():
        description = prompt_loader.get_prompt_description(prompt_path)
        console.print(f"- [cyan]{prompt_path}[/cyan]: {description}")
    console.print()


def generate_test_file(contract_source: str, system_prompt: str = "You are an expert in Sui Move smart contract development.") -> str:
    """
    Generate a test file for a given contract using OpenAI.
    
    Args:
        contract_source: The source code of the contract to generate tests for
        system_prompt: The system prompt to set the model's behavior
        
    Returns:
        Generated test file content
    """
    console.print("[bold green]🧪 Generating test file for the contract...[/bold green]")
    
    prompt = f"""
Given the following Sui Move contract:

```
{contract_source}
```

Generate a comprehensive test file for this contract that covers all key functionality. 
Include tests for happy paths and edge cases.
The test file should follow Sui Move testing best practices and be ready to run with the Sui test framework.
Include helpful comments that explain what each test is checking.
    """
    
    with console.status("[bold blue]Generating tests...[/bold blue]", spinner="dots"):
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
    generated = response.choices[0].message.content
    console.print("[bold green]✅ Test file generation successful![/bold green]")
    return generated


def main():
    """
    Main entry point for the application.
    """
    parser = argparse.ArgumentParser(
        description="Neuromansui: LLM-powered Sui Move contract generator"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="sui_move.base_contract",
        help="Prompt path to use (format: namespace.prompt_name)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available prompts"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum number of iterations for refinement",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save the generated contract to this file path",
    )
    parser.add_argument(
        "--generate-tests",
        action="store_true",
        help="Generate test file for the contract",
    )
    parser.add_argument(
        "--test-output",
        type=str,
        help="Path to save the generated test file (defaults to contract_name_test.move)",
    )
    args = parser.parse_args()

    prompt_loader = PromptLoader()

    if args.list:
        list_available_prompts(prompt_loader)
        return

    prompt_content, system_prompt = prompt_loader.get_prompt(args.prompt)

    if not prompt_content:
        console.print(f"[bold red]Error:[/bold red] Prompt '{args.prompt}' not found.")
        list_available_prompts(prompt_loader)
        return

    console.print(f"[bold blue]Using prompt:[/bold blue] {args.prompt}")
    console.print(f"[blue]Description:[/blue] {prompt_loader.get_prompt_description(args.prompt)}")

    final_contract = iterative_evaluation(
        base_prompt=prompt_content,
        system_prompt=system_prompt,
        max_iterations=args.max_iterations,
    )

    console.print("[bold magenta]=== Final Contract Source ===[/bold magenta]")
    console.print(final_contract)
    
    # Save the contract to a file if output path is provided
    if args.output:
        try:
            output_path = args.output
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            with open(output_path, "w") as f:
                f.write(final_contract)
            console.print(f"[bold green]Contract saved to:[/bold green] {output_path}")
            
            # Generate test file if requested
            if args.generate_tests:
                test_file_content = generate_test_file(final_contract, system_prompt)
                
                # Determine test file path
                if args.test_output:
                    test_output_path = args.test_output
                else:
                    # Default: use the same directory as the contract file but with _test suffix
                    contract_filename = os.path.basename(output_path)
                    contract_name = os.path.splitext(contract_filename)[0]
                    test_output_path = os.path.join(
                        os.path.dirname(output_path), 
                        f"{contract_name}_test.move"
                    )
                
                # Save test file
                with open(test_output_path, "w") as f:
                    f.write(test_file_content)
                console.print(f"[bold green]Test file saved to:[/bold green] {test_output_path}")
        except Exception as e:
            console.print(f"[bold red]Error saving files:[/bold red] {e}")
    elif args.generate_tests:
        console.print("[bold yellow]Warning:[/bold yellow] Cannot generate tests without saving the contract first. Use --output to save the contract.")


if __name__ == "__main__":
    main() 