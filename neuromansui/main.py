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
from typing import Optional, Dict, List
from dotenv import load_dotenv
import openai
from neuromansui.prompt_loader import PromptLoader, collect_errors
import datetime

# Import rich for pretty printing
from rich.console import Console
from rich.table import Table
import re
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

# Import plotly for visualization
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

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
edition = "2024.beta"

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
            # Initialize grouped_errors dictionary
            grouped_errors = {}
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

            result = CompilationResult(
                is_successful=False,
                status_message="[bold red]Compilation Error! ❌[/bold red]",
                feedback=feedback,
                stats={
                    "errors": total_errors,
                    "compiler_warnings": total_compiler_warnings,
                    "linter_warnings": total_linter_warnings,
                },
            )
            
            # Add the parsed error groups to the result as an additional attribute
            result.grouped_errors = grouped_errors
            
            return result
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


def iterative_evaluation(base_prompt: str, system_prompt: str = None, max_iterations: int = 5) -> tuple[str, list]:
    """
    Iteratively calls the LLM to refine the contract source code.
    
    Args:
        base_prompt: The base prompt to use for generation
        system_prompt: The system prompt to set the model's behavior
        max_iterations: Maximum number of iterations to perform
        
    Returns:
        Tuple containing:
        - Final contract source code
        - List of detailed iteration data for fine-tuning
    """
    previous_stats = None
    feedback_text = "Initial run"
    contract_source = ""
    
    # For metrics and fine-tuning data
    iterations_history = []
    fine_tuning_data = []
    
    # Track error codes across iterations
    error_histogram = {}

    if system_prompt is None:
        system_prompt = "You are an expert in Sui Move smart contract development."

    # Create a progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Refining contract...\n", total=max_iterations)
        
        for i in range(max_iterations):
            console.print(f"\n[bold yellow]=== Iteration {i+1}/{max_iterations} ===[/bold yellow]\n")
            full_prompt = base_prompt if i == 0 else f"{base_prompt}\n\nFeedback: {feedback_text}"
            contract_source = generate_contract(full_prompt, system_prompt)
            
            console.print("[bold cyan]Generated contract source:[/bold cyan]")
            console.print(contract_source)

            compiled_result = compile_contract(contract_source)
            console.print("[bold magenta]Compiler Feedback:[/bold magenta]")
            console.print(compiled_result.status_message, highlight=False, markup=True)
            
            # Extract error codes for histogram
            iteration_error_codes = {}
            if not compiled_result.is_successful:
                try:
                    # Get grouped errors directly from the compilation result
                    grouped_errors = getattr(compiled_result, 'grouped_errors', {})
                    
                    # Count occurrences of each error code in this iteration
                    for error_code, errors in grouped_errors.items():
                        # Store both the count and a sample message for the error code
                        sample_message = errors[0].get("msg", "Unknown error")
                        iteration_error_codes[error_code] = {
                            "count": len(errors),
                            "message": sample_message,
                            "level": errors[0].get("level", "Error")
                        }
                        
                        # Update the global histogram
                        if error_code not in error_histogram:
                            error_histogram[error_code] = [0] * max_iterations
                        error_histogram[error_code][i] = len(errors)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not extract error codes: {e}[/yellow]")
                    # In case of error, store error information from the stats instead
                    if compiled_result.stats:
                        error_code = "UNKNOWN_ERROR"
                        count = compiled_result.stats.get("errors", 0)
                        if count > 0:
                            iteration_error_codes[error_code] = {
                                "count": count,
                                "message": "Unknown error",
                                "level": "Error"
                            }
                            if error_code not in error_histogram:
                                error_histogram[error_code] = [0] * max_iterations
                            error_histogram[error_code][i] = count
            
            # Create a record of this iteration for fine-tuning
            iteration_data = {
                "iteration": i+1,
                "prompt": full_prompt,
                "contract_source": contract_source,
                "compiler_output": strip_ansi(compiled_result.feedback.verbose_output),
                "is_successful": compiled_result.is_successful,
                "error_stats": compiled_result.stats,
                "error_codes": iteration_error_codes,
                "timestamp": time.time()
            }
            fine_tuning_data.append(iteration_data)

            # Update iteration metrics
            iteration_metrics = {
                "iteration": i+1,
                "errors": compiled_result.stats.get("errors", 0),
                "compiler_warnings": compiled_result.stats.get("compiler_warnings", 0),
                "linter_warnings": compiled_result.stats.get("linter_warnings", 0),
                "error_codes": iteration_error_codes,
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
        
        # Print error code histogram if errors were found
        if error_histogram:
            console.print("\n[bold blue]== Error Code Histogram ==[/bold blue]")
            histogram_table = Table(title="Error Codes by Iteration")
            histogram_table.add_column("Error Code", style="cyan")
            
            # Add columns for each iteration
            for iter_num in range(1, max_iterations + 1):
                if iter_num <= len(iterations_history):
                    histogram_table.add_column(f"Iter {iter_num}", style="magenta", justify="center")
            
            # Add rows for each error code
            for error_code, counts in error_histogram.items():
                row_data = [error_code]
                for i, count in enumerate(counts):
                    if i < len(iterations_history):
                        row_data.append(str(count) if count > 0 else "-")
                histogram_table.add_row(*row_data)
            
            console.print(histogram_table)

    # Prepare data for stacked bar chart visualization
    iterations_data = []
    for i in range(len(iterations_history)):
        iter_data = {
            "iteration": i + 1,
            "total_errors": iterations_history[i]["errors"],
            "error_breakdown": {}
        }
        
        # Add error breakdown by code
        for error_code, error_info in iterations_history[i]["error_codes"].items():
            if isinstance(error_info, dict):  # New format with message
                count = error_info["count"]
                if count > 0:
                    iter_data["error_breakdown"][error_code] = {
                        "count": count,
                        "message": error_info["message"],
                        "level": error_info["level"]
                    }
            else:  # Old format (just count)
                count = error_info
                if count > 0:
                    iter_data["error_breakdown"][error_code] = {
                        "count": count,
                        "message": "Unknown error",
                        "level": "Error"
                    }
        
        iterations_data.append(iter_data)

    # Add the complete data to fine-tuning data
    fine_tuning_data.append({
        "error_histogram": error_histogram,
        "iterations_data": iterations_data,  # Add data formatted for stacked bar chart
        "total_iterations": len(iterations_history)
    })

    return contract_source, fine_tuning_data


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


def generate_error_chart(iterations_data: List[dict], output_path: str, dark_mode: bool = False, all_contracts: List[str] = None, initial_prompt: str = None, iteration_prompts: List[str] = None) -> None:
    """
    Generate an interactive Plotly visualization of error codes by iteration.
    
    Args:
        iterations_data: List of dictionaries containing iteration data
        output_path: Path to save the HTML visualization
        dark_mode: Whether to use dark mode for the visualization
        all_contracts: List of contract source code for each iteration
        initial_prompt: The initial prompt given to the LLM
        iteration_prompts: List of prompts for each iteration
    """
    if not iterations_data:
        return
    
    # Sort iterations by number to ensure order
    iterations_data.sort(key=lambda x: x["iteration"])
    
    # Get the list of all error codes across all iterations
    all_error_codes = set()
    for iteration in iterations_data:
        all_error_codes.update(iteration["error_breakdown"].keys())
    all_error_codes = sorted(all_error_codes)
    
    # Create a mapping of error codes to their descriptions (from sample messages)
    error_descriptions = {}
    for iteration in iterations_data:
        for error_code, error_info in iteration["error_breakdown"].items():
            if error_code not in error_descriptions and isinstance(error_info, dict):
                # Use the actual sample message from the compiler
                message = error_info.get("message", "Unknown error")
                level = error_info.get("level", "Error")
                
                # Prefix the description with the error level category
                if "BlockingError" in level:
                    prefix = "Error"
                elif "NonblockingError" in level:
                    prefix = "Non-blocking Error"
                elif "Warning" in level:
                    prefix = "Warning"
                elif "Lint" in error_code:
                    prefix = "Lint Warning"
                else:
                    prefix = level
                
                error_descriptions[error_code] = f"{prefix}: {message}"
    
    # Calculate aggregate statistics by error category
    error_categories = {
        "Blocking Errors": 0,
        "Non-blocking Errors": 0, 
        "Warnings": 0,
        "Lint Warnings": 0,
        "Other": 0
    }
    
    # Track most frequent errors
    error_frequency = {}
    
    # Calculate total errors by type and frequency
    for error_code in all_error_codes:
        total_occurrences = 0
        error_category = None
        
        # Find the category for this error code
        for iteration in iterations_data:
            if error_code in iteration["error_breakdown"]:
                error_info = iteration["error_breakdown"][error_code]
                
                # Get count
                if isinstance(error_info, dict):
                    count = error_info["count"]
                    level = error_info.get("level", "")
                else:
                    count = error_info
                    level = ""
                
                # Add to total
                total_occurrences += count
                
                # Determine category if not already set
                if error_category is None:
                    if "BlockingError" in level:
                        error_category = "Blocking Errors"
                    elif "NonblockingError" in level:
                        error_category = "Non-blocking Errors"
                    elif "Warning" in level:
                        error_category = "Warnings"
                    elif "Lint" in error_code:
                        error_category = "Lint Warnings"
                    else:
                        error_category = "Other"
        
        # Add to category totals
        if error_category:
            error_categories[error_category] += total_occurrences
        else:
            # Fallback categorization based on code prefix
            if error_code.startswith("E"):
                error_categories["Blocking Errors"] += total_occurrences
            elif error_code.startswith("N"):
                error_categories["Non-blocking Errors"] += total_occurrences
            elif error_code.startswith("W"):
                error_categories["Warnings"] += total_occurrences
            elif "Lint" in error_code:
                error_categories["Lint Warnings"] += total_occurrences
            else:
                error_categories["Other"] += total_occurrences
        
        # Track frequency
        error_frequency[error_code] = {
            "count": total_occurrences,
            "description": error_descriptions.get(error_code, error_code)
        }
    
    # Get top 3 most frequent errors
    top_errors = sorted(error_frequency.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
    
    # Color gradients for each type - using HSL to ensure perceptual distinction
    # For dark mode, we'll use slightly different hues and higher lightness
    if dark_mode:
        # Dark mode palettes (higher lightness for better visibility on dark backgrounds)
        non_blocking_palette = [(0, 90, 60), (10, 85, 65)]  # Red hues (now for non-blocking)
        error_palette = [(25, 90, 60), (35, 85, 65)]  # Orange hues (now for blocking errors)
        warning_palette = [(40, 75, 60), (50, 70, 65)]  # Yellow hues
        lint_palette = [(200, 75, 65), (220, 70, 70)]  # Blue hues
        other_palette = [(290, 50, 65), (310, 50, 70)]  # Purple hues
    else:
        # Light mode palettes
        non_blocking_palette = [(0, 90, 50), (10, 85, 55)]  # Red hues (now for non-blocking)
        error_palette = [(25, 90, 50), (35, 85, 55)]  # Orange hues (now for blocking errors)
        warning_palette = [(40, 75, 45), (50, 70, 50)]  # Yellow hues
        lint_palette = [(200, 75, 55), (220, 70, 60)]  # Blue hues
        other_palette = [(290, 50, 55), (310, 50, 60)]  # Purple hues
    
    # Group error codes by type for color assignment
    error_types = {
        "Error": [],
        "NonBlocking": [],
        "Warning": [],
        "Lint": [],
        "Other": []
    }

    # Categorize each error code by its type
    for error_code in all_error_codes:
        if error_code.startswith("E"):
            error_types["Error"].append(error_code)
        elif error_code.startswith("N"):
            error_types["NonBlocking"].append(error_code)
        elif error_code.startswith("W") and "Lint" not in error_code:
            error_types["Warning"].append(error_code)
        elif "Lint" in error_code:
            error_types["Lint"].append(error_code)
        else:
            error_types["Other"].append(error_code)

    # Initialize dictionary to hold the color for each error code
    error_colors = {}

    # Assign colors based on gradients for each type
    for type_name, codes in error_types.items():
        if not codes:
            continue
            
        if type_name == "Error":
            palette = error_palette
        elif type_name == "NonBlocking":
            palette = non_blocking_palette
        elif type_name == "Warning":
            palette = warning_palette
        elif type_name == "Lint":
            palette = lint_palette
        else:
            palette = other_palette
            
        # Create gradient steps
        num_codes = len(codes)
        for i, code in enumerate(codes):
            # Interpolate between palette start and end based on position
            t = i / max(1, num_codes - 1)  # Avoid division by zero
            h = palette[0][0] + t * (palette[1][0] - palette[0][0])
            s = palette[0][1] + t * (palette[1][1] - palette[0][1])
            l = palette[0][2] + t * (palette[1][2] - palette[0][2])
            error_colors[code] = f"hsl({h}, {s}%, {l}%)"
    
    # Prepare data for the stacked bar chart
    fig = go.Figure()
    
    # Add traces, one for each error code
    for error_code in all_error_codes:
        y_values = []
        for iteration in iterations_data:
            error_info = iteration["error_breakdown"].get(error_code, 0)
            if isinstance(error_info, dict):
                y_values.append(error_info["count"])
            else:
                y_values.append(error_info)  # For backward compatibility
        
        # Add hover text with more information
        hover_texts = []
        for i, count in enumerate(y_values):
            if count > 0:
                # Get details for this particular error
                error_info = iterations_data[i]["error_breakdown"].get(error_code)
                message = error_info.get("message", "Unknown error") if isinstance(error_info, dict) else "Unknown error"
                level = error_info.get("level", "Error") if isinstance(error_info, dict) else "Error"
                
                hover_texts.append(f"<b>Iteration {iterations_data[i]['iteration']}</b><br>"
                                  f"Error code: <b>{error_code}</b><br>"
                                  f"Level: <b>{level}</b><br>"
                                  f"Message: <b>{message}</b><br>"
                                  f"Count: <b>{count}</b><br>"
                                  f"Percentage: <b>{(count/iterations_data[i]['total_errors'])*100:.1f}%</b>")
            else:
                hover_texts.append(f"<b>Iteration {iterations_data[i]['iteration']}</b><br>"
                                  f"Error code: <b>{error_code}</b><br>"
                                  f"Count: <b>0</b>")
        
        # Use descriptive names in the legend instead of error codes
        legend_name = error_descriptions.get(error_code, error_code)
        
        fig.add_trace(go.Bar(
            name=legend_name,
            x=[f"Iteration {i['iteration']}" for i in iterations_data],
            y=y_values,
            marker_color=error_colors[error_code],
            hovertemplate="%{text}<extra></extra>",
            text=hover_texts
        ))
    
    # Calculate progress statistics
    first_iter = iterations_data[0]
    last_iter = iterations_data[-1]
    first_iter_errors = first_iter["total_errors"]
    last_iter_errors = last_iter["total_errors"]
    
    # Calculate percentage improvement
    improvement_pct = 0
    if first_iter_errors > 0:
        improvement_pct = ((first_iter_errors - last_iter_errors) / first_iter_errors) * 100
    
    # Set background colors based on mode
    if dark_mode:
        bg_color = '#111827'  # Dark gray
        text_color = '#F9FAFB'  # Light gray
        grid_color = 'rgba(255, 255, 255, 0.1)'
        template = 'plotly_dark'
        stats_bg_color = 'rgba(31, 41, 55, 0.8)'  # Slightly lighter than background
        stats_border_color = 'rgba(75, 85, 99, 0.5)'  # Gray border
    else:
        bg_color = 'white'
        text_color = '#333'
        grid_color = 'rgba(0, 0, 0, 0.1)'
        template = 'plotly_white'
        stats_bg_color = 'rgba(245, 247, 250, 0.85)'  # Light gray/blue
        stats_border_color = 'rgba(200, 200, 200, 0.5)'  # Light gray border
    
    # Add summary statistics box in the top right corner
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.99, y=0.99,
        xanchor="right", yanchor="top",
        text=(
            f"<b>Summary Statistics</b><br>"
            f"Total Errors: {sum(c for c in error_categories.values())}<br>"
            f"Blocking Errors: {error_categories['Blocking Errors']}<br>"
            f"Non-blocking Errors: {error_categories['Non-blocking Errors']}<br>"
            f"Warnings: {error_categories['Warnings']}<br>"
            f"Lint Warnings: {error_categories['Lint Warnings']}<br>"
            f"Overall Improvement: {improvement_pct:.1f}%<br>"
            f"<b>Top Errors:</b><br>" + 
            "<br>".join([f"{i+1}. {details['description']} ({details['count']})" 
                         for i, (_, details) in enumerate(top_errors)])
        ),
        showarrow=False,
        bordercolor=stats_border_color,
        borderwidth=2,
        borderpad=10,
        bgcolor=stats_bg_color,
        opacity=0.9,
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color=text_color
        )
    )
    
    # Customize layout for a modern, slick look
    fig.update_layout(
        title={
            'text': 'Evolution of Compiler Errors Across Iterations',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24, 'family': 'Arial, sans-serif', 'color': '#3B82F6' if dark_mode else '#1E3A8A'}
        },
        barmode='stack',
        xaxis_title={'text': 'Iteration', 'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': text_color}},
        yaxis_title={'text': 'Number of Errors', 'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': text_color}},
        legend_title={'text': 'Error Types', 'font': {'size': 14, 'family': 'Arial, sans-serif', 'color': text_color}},
        template=template,
        hovermode='closest',
        height=800,
        margin=dict(t=100, b=100, l=100, r=100),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font={'family': 'Arial, sans-serif', 'color': text_color},
        legend={
            'bgcolor': 'rgba(255, 255, 255, 0.1)' if dark_mode else 'rgba(255, 255, 255, 0.5)',
            'bordercolor': 'rgba(255, 255, 255, 0.2)' if dark_mode else 'rgba(0, 0, 0, 0.1)',
            'borderwidth': 1,
            'orientation': 'v',  # Vertical orientation for right side placement
            'yanchor': 'middle',
            'y': 0.5,  # Center vertically
            'xanchor': 'left',
            'x': 1.02  # Place just outside the right edge of the plot
        },
        # Add a watermark-like subtitle
        annotations=[
            dict(
                text="Sui Move Compiler Error Analysis",
                xref="paper",
                yref="paper",
                x=0.5,
                y=1.05,
                showarrow=False,
                font=dict(
                    family="Arial, sans-serif",
                    size=14,
                    color='rgba(255, 255, 255, 0.4)' if dark_mode else 'rgba(0, 0, 0, 0.2)'
                )
            )
        ]
    )
    
    # Add a trend line showing the total errors per iteration
    total_errors = [i["total_errors"] for i in iterations_data]
    
    # Get successful iterations (where total_errors is 0)
    successful_iterations = [i for i, errors in enumerate(total_errors) if errors == 0]
    
    # Add the trend line
    fig.add_trace(go.Scatter(
        x=[f"Iteration {i['iteration']}" for i in iterations_data],
        y=total_errors,
        mode='lines+markers',
        name='Total Errors',
        line=dict(color='#EF4444' if dark_mode else 'red', width=3, dash='solid'),
        marker=dict(size=10, symbol='diamond', color='#B91C1C' if dark_mode else 'darkred'),
        hovertemplate="<b>%{x}</b><br>Total Errors: <b>%{y}</b><extra></extra>"
    ))
    
    # Add markers for successful iterations
    if successful_iterations:
        successful_x = [f"Iteration {iterations_data[i]['iteration']}" for i in successful_iterations]
        successful_y = [0] * len(successful_iterations)
        
        fig.add_trace(go.Scatter(
            x=successful_x,
            y=successful_y,
            mode='markers',
            name='Success',
            marker=dict(
                symbol='star',
                size=16,
                color='#22C55E',  # Green
                line=dict(width=2, color='#14532D')
            ),
            hovertemplate="<b>%{x}</b><br>Successfully compiled!<extra></extra>"
        ))
    
    # Add annotations showing percentage improvement between iterations
    for i in range(1, len(total_errors)):
        if total_errors[i-1] > 0:  # Avoid division by zero
            change_pct = ((total_errors[i] - total_errors[i-1]) / total_errors[i-1]) * 100
            # Show both improvements and regressions with different colors
            if change_pct < 0:
                arrow_color = "#22C55E"  # Green for improvement
                text_color = "#22C55E"
            else:
                arrow_color = "#EF4444"  # Red for regression
                text_color = "#EF4444"
                
            fig.add_annotation(
                x=i,
                y=(total_errors[i] + total_errors[i-1]) / 2,
                text=f"{change_pct:.1f}%",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=arrow_color,
                font=dict(size=12, color=text_color),
                ax=40,
                ay=0
            )
    
    # Add grid lines
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=grid_color,
        tickangle=0
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=grid_color
    )
    
    # Add labels showing exact error counts above each bar
    for i, _ in enumerate(iterations_data):
        if total_errors[i] > 0:
            fig.add_annotation(
                x=i,
                y=total_errors[i] + 1,  # Position slightly above the bar
                text=str(total_errors[i]),
                showarrow=False,
                font=dict(
                    size=14, 
                    color='#F9FAFB' if dark_mode else '#111827'
                )
            )
            
    # Save the figure as an HTML file with embedded contract code
    html_path = f"{output_path}_error_chart{'_dark' if dark_mode else ''}.html"
    
    # If we have contract source code, create an HTML file with tabs
    if all_contracts and len(all_contracts) > 0:
        # Create HTML with tabs for the chart and each iteration's source code
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sui Move Contract Analysis</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/{'atom-one-dark.min.css' if dark_mode else 'github.min.css'}">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/languages/rust.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/languages/bash.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/languages/toml.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/languages/markdown.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: {bg_color};
                    color: {text_color};
                }}
                .container {{
                    width: 95%;
                    margin: 20px auto;
                    min-height: 85vh; /* Ensure container takes up most of the viewport height */
                }}
                .tab {{
                    overflow: hidden;
                    border: 1px solid {'#2D3748' if dark_mode else '#ccc'};
                    background-color: {'#1F2937' if dark_mode else '#f1f1f1'};
                    border-radius: 5px 5px 0 0;
                }}
                .tab button {{
                    background-color: inherit;
                    float: left;
                    border: none;
                    outline: none;
                    cursor: pointer;
                    padding: 14px 16px;
                    transition: 0.3s;
                    font-size: 16px;
                    color: {text_color};
                }}
                .tab button:hover {{
                    background-color: {'#374151' if dark_mode else '#ddd'};
                }}
                .tab button.active {{
                    background-color: {'#4B5563' if dark_mode else '#ccc'};
                }}
                .tabcontent {{
                    display: none;
                    padding: 6px 12px;
                    border: 1px solid {'#2D3748' if dark_mode else '#ccc'};
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                    animation: fadeEffect 1s;
                    background-color: {'#1F2937' if dark_mode else '#fff'};
                    min-height: 70vh; /* Ensure tab content area is tall enough */
                }}
                @keyframes fadeEffect {{
                    from {{opacity: 0;}}
                    to {{opacity: 1;}}
                }}
                pre {{
                    margin: 0;
                    padding: 16px;
                    overflow: auto;
                    border-radius: 4px;
                }}
                code {{
                    font-family: 'Courier New', Courier, monospace;
                }}
                .hljs-line-numbers {{
                    text-align: right;
                    padding-right: 10px;
                    color: {'#6B7280' if dark_mode else '#999'};
                    border-right: 1px solid {'#4B5563' if dark_mode else '#ddd'};
                    margin-right: 10px;
                    user-select: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="text-align: center; color: {'#3B82F6' if dark_mode else '#1E3A8A'};">Sui Move Contract Analysis</h1>
                
                <div class="tab" id="tabs">
                    <button class="tablinks active" id="ErrorChartTab">Error Chart</button>
        """
        
        # Add buttons for each iteration
        for i, contract in enumerate(all_contracts):
            if contract:  # Only add tabs for non-empty contracts
                html_content += f"""
                    <button class="tablinks" id="Iteration{i+1}Tab">Iteration {i+1}</button>
                """
        
        html_content += """
                </div>
                
                <div id="ErrorChart" class="tabcontent" style="display: block;">
                    <div id="plotly-chart"></div>
        """
        
        # Add initial prompt console card if available
        if initial_prompt:
            console_bg_color = "#1E293B" if dark_mode else "#F1F5F9"
            console_text_color = "#E2E8F0" if dark_mode else "#334155"
            console_border = "#475569" if dark_mode else "#CBD5E1"
            
            html_content += f"""
                    <div class="prompt-console" style="margin-top: 30px; margin-bottom: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <div class="console-header" style="background-color: {console_bg_color}; padding: 10px 15px; border-bottom: 1px solid {console_border};">
                            <div style="display: flex; align-items: center;">
                                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #EF4444; margin-right: 8px;"></div>
                                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #F59E0B; margin-right: 8px;"></div>
                                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #10B981; margin-right: 8px;"></div>
                                <span style="color: {console_text_color}; font-family: 'Arial', sans-serif; font-size: 14px;">Initial Prompt</span>
                            </div>
                        </div>
                        <div class="console-body" style="background-color: {console_bg_color}; padding: 15px; max-height: 350px; overflow-y: auto;">
                            <pre style="margin: 0; white-space: pre-wrap; color: {console_text_color}; font-family: 'Courier New', monospace; font-size: 14px;">{escape_html(initial_prompt)}</pre>
                        </div>
                    </div>
            """
        
        html_content += """
                </div>
        """
        
        # Add content for each iteration
        for i, contract in enumerate(all_contracts):
            if contract:  # Only add content for non-empty contracts
                # Get the prompt for this iteration if available
                iteration_prompt = None
                if iteration_prompts and i < len(iteration_prompts):
                    iteration_prompt = iteration_prompts[i]
                
                html_content += f"""
                <div id="Iteration{i+1}" class="tabcontent">
                    <h3>Contract Source - Iteration {i+1}</h3>
                """
                
                # Add the prompt for this iteration if available
                if iteration_prompt:
                    console_bg_color = "#1E293B" if dark_mode else "#F1F5F9"
                    console_text_color = "#E2E8F0" if dark_mode else "#334155"
                    console_border = "#475569" if dark_mode else "#CBD5E1"
                    
                    html_content += f"""
                    <div class="iteration-prompt" style="margin-bottom: 20px;">
                        <h4>Prompt for Iteration {i+1}</h4>
                        <div class="prompt-console" style="border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                            <div class="console-header" style="background-color: {console_bg_color}; padding: 8px 12px; border-bottom: 1px solid {console_border};">
                                <div style="display: flex; align-items: center;">
                                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: #EF4444; margin-right: 6px;"></div>
                                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: #F59E0B; margin-right: 6px;"></div>
                                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: #10B981; margin-right: 6px;"></div>
                                    <span style="color: {console_text_color}; font-family: 'Arial', sans-serif; font-size: 12px;">Prompt</span>
                                </div>
                            </div>
                            <div class="console-body" style="background-color: {console_bg_color}; padding: 12px; max-height: 200px; overflow-y: auto;">
                                <pre style="margin: 0; white-space: pre-wrap; color: {console_text_color}; font-family: 'Courier New', monospace; font-size: 12px;">{escape_html(iteration_prompt)}</pre>
                            </div>
                        </div>
                    </div>
                    """
                
                # Add syntax highlighting with line numbers for the contract code
                html_content += f"""
                    <pre><code class="language-rust hljs">{escape_html(contract)}</code></pre>
                </div>
                """
        
        # Add JavaScript for the tabs and syntax highlighting
        html_content += """
                <script>
                    // Legacy function for backward compatibility
                    function openTab(evt, tabName) {
                        var i, tabcontent, tablinks;
                        tabcontent = document.getElementsByClassName("tabcontent");
                        for (i = 0; i < tabcontent.length; i++) {
                            tabcontent[i].style.display = "none";
                        }
                        tablinks = document.getElementsByClassName("tablinks");
                        for (i = 0; i < tablinks.length; i++) {
                            tablinks[i].className = tablinks[i].className.replace(" active", "");
                        }
                        document.getElementById(tabName).style.display = "block";
                        evt.currentTarget.className += " active";
                    }

                    // Tab handling functions
                    document.addEventListener('DOMContentLoaded', function() {
                        // First, hide all tab contents
                        var tabcontents = document.getElementsByClassName("tabcontent");
                        for (var i = 0; i < tabcontents.length; i++) {
                            tabcontents[i].style.display = "none";
                        }
                        
                        // Show the default tab
                        document.getElementById("ErrorChart").style.display = "block";
                        
                        // Setup click handlers for tabs
                        var tabs = document.getElementById("tabs").getElementsByTagName("button");
                        for (var i = 0; i < tabs.length; i++) {
                            tabs[i].addEventListener("click", function() {
                                // Remove active class from all tabs
                                for (var j = 0; j < tabs.length; j++) {
                                    tabs[j].className = tabs[j].className.replace(" active", "");
                                }
                                
                                // Add active class to clicked tab
                                this.className += " active";
                                
                                // Hide all tab contents
                                for (var j = 0; j < tabcontents.length; j++) {
                                    tabcontents[j].style.display = "none";
                                }
                                
                                // Show the corresponding tab content
                                var tabId = this.id.replace("Tab", "");
                                document.getElementById(tabId).style.display = "block";
                            });
                        }
                    });
                    
                    // Add line numbers to code blocks
                    function addLineNumbers() {
                        var codeBlocks = document.querySelectorAll('pre code');
                        codeBlocks.forEach(function(codeBlock) {
                            var lines = codeBlock.innerHTML.split('\\n');
                            var numbered = lines.map(function(line, i) {
                                return '<span class="hljs-line-numbers">' + (i + 1) + '</span>' + line;
                            }).join('\\n');
                            codeBlock.innerHTML = numbered;
                        });
                    }
                    
                    document.addEventListener('DOMContentLoaded', function() {
                        // Initialize syntax highlighting
                        hljs.highlightAll();
                        // Add line numbers after highlighting
                        addLineNumbers();
                        
                        // Process code blocks in prompts
                        processPromptCodeBlocks();
                    });
                    
                    // Function to process code blocks in prompts
                    function processPromptCodeBlocks() {
                        // Find all prompt pre elements
                        const promptPres = document.querySelectorAll('.console-body pre');
                        
                        promptPres.forEach(function(pre) {
                            try {
                                // Use a safer string-based approach instead of regex
                                let content = pre.innerHTML;
                                let processed = content;
                                
                                // Find the start positions of all code blocks
                                const codeBlockStarts = [];
                                let searchPos = 0;
                                let foundPos;
                                
                                while ((foundPos = content.indexOf("```", searchPos)) !== -1) {
                                    codeBlockStarts.push(foundPos);
                                    searchPos = foundPos + 3;
                                }
                                
                                // Process code blocks in reverse order to avoid position shifts
                                if (codeBlockStarts.length >= 2 && codeBlockStarts.length % 2 === 0) {
                                    for (let i = codeBlockStarts.length - 2; i >= 0; i -= 2) {
                                        const blockStart = codeBlockStarts[i];
                                        const blockEnd = codeBlockStarts[i + 1];
                                        
                                        // Extract the entire block including markers
                                        const fullBlock = content.substring(blockStart, blockEnd + 3);
                                        
                                        // Extract language (if any)
                                        let lang = 'plaintext';
                                        const firstLineEnd = fullBlock.indexOf('');
                                        if (firstLineEnd > 3) { // There's content after the opening ```
                                            lang = fullBlock.substring(3, firstLineEnd).trim() || 'plaintext';
                                        }
                                        
                                        // Extract code content (between the markers)
                                        const codeStart = fullBlock.indexOf('') + 1;
                                        const codeEnd = fullBlock.lastIndexOf("```");
                                        const code = fullBlock.substring(codeStart, codeEnd);
                                        
                                        // Create the replacement HTML
                                        const replacement = `<div class="prompt-code-block" style="margin: 10px 0; border-radius: 4px; overflow: hidden;">
                                          <div style="padding: 6px 10px; background-color: rgba(0,0,0,0.2); font-size: 12px; border-bottom: 1px solid rgba(0,0,0,0.1);">${lang}</div>
                                          <pre style="margin: 0; padding: 10px;"><code class="language-${lang}">${code}</code></pre>
                                        </div>`;
                                        
                                        // Replace the code block with the HTML
                                        processed = processed.replace(fullBlock, replacement);
                                    }
                                }
                                
                                if (content !== processed) {
                                    pre.innerHTML = processed;
                                    // Apply highlighting to the newly created code blocks
                                    pre.querySelectorAll('code').forEach(function(block) {
                                        hljs.highlightElement(block);
                                    });
                                }
                            } catch (error) {
                                console.log("Error processing code blocks:", error);
                            }
                        });
                    }
                </script>
        """
        
        # Add the Plotly figure
        fig_json = fig.to_json()
        html_content += f"""
                <script>
                    var figure = {fig_json};
                    Plotly.newPlot('plotly-chart', figure.data, figure.layout, {{
                        displayModeBar: true,
                        responsive: true,
                        displaylogo: false,
                        toImageButtonOptions: {{
                            format: 'png',
                            filename: 'error_chart{"_dark" if dark_mode else ""}',
                            height: 800,
                            width: 1200,
                            scale: 2
                        }}
                    }});
                </script>
            </div>
        </body>
        </html>
        """
        
        # Write the HTML to file
        with open(html_path, "w") as f:
            f.write(html_content)
    else:
        # If we don't have contract source code, save just the figure
        fig.write_html(
            html_path,
            include_plotlyjs='cdn',
            full_html=True,
            config={
                'displayModeBar': True,
                'responsive': True,
                'displaylogo': False,
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': f'error_chart{"_dark" if dark_mode else ""}',
                    'height': 800,
                    'width': 1200,
                    'scale': 2
                }
            }
        )
    
    # Generate the alternate version only if explicitly requested
    # This prevents infinite recursion
    console.print(f"[bold green]Error visualization saved to:[/bold green] {html_path}")
    
    return fig


def escape_html(text):
    """Escape HTML special characters in text."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#039;"))


def save_fine_tuning_data(fine_tuning_data: list, output_path: str, dark_mode: bool = False):
    """
    Save fine-tuning data to a file in a format suitable for model training.
    
    Args:
        fine_tuning_data: List of iteration data
        output_path: Base path to save the file (without extension)
        dark_mode: Whether to use dark mode for visualizations
    """
    # Format the data for fine-tuning
    training_examples = []
    
    # Extract the error histogram data (should be the last item in fine_tuning_data)
    error_histogram = {}
    iterations_data = []
    total_iterations = 0
    contract_versions = []  # Store each version of the contract
    iteration_prompts = []  # Store prompts for each iteration
    initial_prompt = None   # Store the initial prompt
    
    if fine_tuning_data and isinstance(fine_tuning_data[-1], dict) and "error_histogram" in fine_tuning_data[-1]:
        error_histogram = fine_tuning_data[-1]["error_histogram"]
        iterations_data = fine_tuning_data[-1].get("iterations_data", [])
        total_iterations = fine_tuning_data[-1]["total_iterations"]
        # Remove the histogram data from the list
        fine_tuning_data = fine_tuning_data[:-1]
    
    # Extract each version of the contract and prompts for visualization
    for i, iteration in enumerate(fine_tuning_data):
        if "contract_source" in iteration:
            contract_versions.append(iteration["contract_source"])
        else:
            # If this iteration doesn't have contract source, add None as placeholder
            contract_versions.append(None)
            
        # Extract prompts for each iteration
        if "prompt" in iteration:
            iteration_prompts.append(iteration["prompt"])
            # Store the initial prompt separately
            if i == 0:
                initial_prompt = iteration["prompt"]
        else:
            iteration_prompts.append(None)
        
        if not iteration["is_successful"]:
            # For unsuccessful iterations, we create a training example
            # Input: the buggy contract, Output: the compiler errors
            training_example = {
                "input": iteration["contract_source"],
                "output": iteration["compiler_output"],
                "metadata": {
                    "iteration": iteration["iteration"],
                    "timestamp": iteration["timestamp"],
                    "error_stats": iteration["error_stats"],
                    "error_codes": iteration.get("error_codes", {})
                }
            }
            training_examples.append(training_example)
    
    # Format the full dataset with metadata
    dataset = {
        "version": "1.0",
        "created_at": datetime.datetime.now().isoformat(),
        "description": "Sui Move compiler error prediction dataset",
        "examples": training_examples,
        "error_histogram": error_histogram,
        "iterations_data": iterations_data,  # Add data formatted for stacked bar chart
        "total_iterations": total_iterations
    }
    
    # Save to JSONL for fine-tuning - correct format with one messages array per entry
    system_message = "You are a Sui Move compiler. Your task is to analyze the provided contract and output any compilation errors."
    jsonl_path = f"{output_path}.jsonl"
    with open(jsonl_path, "w") as f:
        for example in training_examples:
            # Each line has one messages array containing the system, user, and assistant messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": example["input"]},
                {"role": "assistant", "content": example["output"]}
            ]
            f.write(json.dumps({"messages": messages}) + "\n")
    
    # Also save the full dataset to JSON for reference
    json_path = f"{output_path}.json"
    with open(json_path, "w") as f:
        json.dump(dataset, f, indent=2)
    
    # Generate the error chart visualization
    if iterations_data:
        try:
            generate_error_chart(iterations_data, output_path, dark_mode, contract_versions, initial_prompt=initial_prompt, iteration_prompts=iteration_prompts)
            
            # Generate the alternate theme version if requested
            if not dark_mode:
                alt_path = f"{output_path}_error_chart_dark.html"
                if not os.path.exists(alt_path):
                    generate_error_chart(iterations_data, output_path, True, contract_versions, initial_prompt=initial_prompt, iteration_prompts=iteration_prompts)
                    console.print(f"[bold green]Dark mode visualization also available at:[/bold green] {alt_path}")
            else:
                alt_path = f"{output_path}_error_chart.html"
                if not os.path.exists(alt_path):
                    generate_error_chart(iterations_data, output_path, False, contract_versions, initial_prompt=initial_prompt, iteration_prompts=iteration_prompts)
                    console.print(f"[bold green]Light mode visualization also available at:[/bold green] {alt_path}")
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate error chart: {e}. Make sure plotly is installed.[/yellow]")
    
    console.print(f"[bold green]Fine-tuning data saved to:[/bold green] {jsonl_path}")
    console.print(f"[bold green]Complete dataset saved to:[/bold green] {json_path}")


def main():
    """
    Main entry point for the application.
    """
    parser = argparse.ArgumentParser(
        description="Neuromansui: LLM-powered Sui Move contract generator and refiner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available prompts
  python -m neuromansui.main --list
  
  # Generate a contract with default settings
  python -m neuromansui.main --prompt sui_move.base_contract
  
  # Generate a contract with custom settings and save outputs
  python -m neuromansui.main --prompt sui_move.nft_contract --module-name my_nft --save-dir my_contracts --max-iterations 8 --dark-mode
  
  # Generate a contract with tests and visualizations
  python -m neuromansui.main --prompt sui_move.defi_contract --generate-tests --save-iterations --dark-mode
        """
    )

    # Create argument groups for better organization
    info_group = parser.add_argument_group('Information')
    input_group = parser.add_argument_group('Input Options')
    output_group = parser.add_argument_group('Output Options')
    vis_group = parser.add_argument_group('Visualization Options')
    
    # Information arguments
    info_group.add_argument(
        "--list", 
        action="store_true", 
        help="List all available prompts and exit"
    )
    info_group.add_argument(
        "--version", 
        action="version", 
        version="Neuromansui v0.1.0",
        help="Show version information and exit"
    )

    # Input arguments
    input_group.add_argument(
        "--prompt",
        type=str,
        default="sui_move.base_contract",
        metavar="NAMESPACE.NAME",
        help="Prompt to use for contract generation (default: sui_move.base_contract)"
    )
    input_group.add_argument(
        "--module-name",
        type=str,
        default="my_module",
        metavar="NAME",
        help="Name of the module to generate (default: my_module)"
    )
    input_group.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        metavar="NUM",
        help="Maximum number of refinement iterations (default: 5)"
    )

    # Output arguments
    output_group.add_argument(
        "--save-dir",
        type=str,
        default="test_outputs",
        metavar="DIR",
        help="Directory to save all output files (default: test_outputs)"
    )
    output_group.add_argument(
        "--name",
        type=str,
        metavar="NAME",
        help="Base name for output files (default: auto-generated from prompt name and timestamp)"
    )
    output_group.add_argument(
        "--generate-tests",
        action="store_true",
        help="Generate test file for the contract"
    )
    output_group.add_argument(
        "--save-iterations",
        action="store_true",
        help="Save all iteration data for fine-tuning and visualization"
    )
    
    # Visualization arguments
    vis_group.add_argument(
        "--dark-mode",
        action="store_true",
        help="Use dark mode for visualizations"
    )
    
    # Legacy/deprecated arguments - hidden from help but still functional
    parser.add_argument(
        "--output",
        type=str,
        help=argparse.SUPPRESS  # Hide from help
    )
    parser.add_argument(
        "--test-output",
        type=str,
        help=argparse.SUPPRESS  # Hide from help
    )
    parser.add_argument(
        "--iterations-output",
        type=str,
        help=argparse.SUPPRESS  # Hide from help
    )
    
    args = parser.parse_args()

    prompt_loader = PromptLoader()

    if args.list:
        list_available_prompts(prompt_loader)
        return

    if args.output:
        console.print("[bold yellow]Warning:[/bold yellow] --output is deprecated. Please use --save-dir and --name instead.")

    if args.test_output:
        console.print("[bold yellow]Warning:[/bold yellow] --test-output is deprecated. Please use --save-dir and --name instead.")
        
    if args.iterations_output:
        console.print("[bold yellow]Warning:[/bold yellow] --iterations-output is deprecated. Please use --save-dir and --name instead.")

    prompt_content, system_prompt = prompt_loader.get_prompt(args.prompt)

    if not prompt_content:
        console.print(f"[bold red]Error:[/bold red] Prompt '{args.prompt}' not found.")
        list_available_prompts(prompt_loader)
        return

    console.print(f"[bold blue]Using prompt:[/bold blue] {args.prompt}")
    console.print(f"[blue]Description:[/blue] {prompt_loader.get_prompt_description(args.prompt)}")

    # Create the Move.toml file template that will be used
    move_toml = f"""
[package]
name = "TempContract"
version = "0.0.1"
edition = "2024.beta"

[dependencies]
Sui = {{ git = "https://github.com/MystenLabs/sui.git", subdir = "crates/sui-framework/packages/sui-framework", rev = "framework/testnet" }}

[addresses]
temp_addr = "0x0"
"""

    # Enhance the prompt with the Move.toml content and module name
    enhanced_prompt = f"""
# Move.toml configuration:
```
{move_toml}
```

# Module Name:
You should create a module named '{args.module_name}'

# Original Prompt:
{prompt_content}
"""

    final_contract, fine_tuning_data = iterative_evaluation(
        base_prompt=enhanced_prompt,
        system_prompt=system_prompt,
        max_iterations=args.max_iterations,
    )

    console.print("[bold magenta]=== Final Contract Source ===[/bold magenta]")
    console.print(final_contract)
    
    # Determine if we should save files
    should_save = args.output or (args.save_dir is not None)
    
    if should_save:
        try:
            # Determine the output path
            if args.output:
                # Legacy output path
                output_path = args.output
                output_dir = os.path.dirname(os.path.abspath(output_path))
                output_basename = os.path.basename(output_path)
                contract_name = os.path.splitext(output_basename)[0]
            else:
                # New output path based on save-dir and name
                output_dir = args.save_dir
                
                # Generate a name if not provided
                if args.name:
                    contract_name = args.name
                else:
                    # Create a name based on prompt and timestamp
                    prompt_part = args.prompt.split('.')[-1]  # Take the last part of the prompt path
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    contract_name = f"{prompt_part}_{timestamp}"
                
                # Full path for the contract file
                output_path = os.path.join(output_dir, f"{contract_name}.move")
            
            # Ensure the directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Check if the file already exists and ask for confirmation
            if os.path.exists(output_path):
                console.print(f"[bold yellow]Warning:[/bold yellow] File {output_path} already exists.")
                overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
                if overwrite != 'y':
                    console.print("[yellow]Aborted saving operation.[/yellow]")
                    return
            
            # Save the contract
            with open(output_path, "w") as f:
                f.write(final_contract)
            console.print(f"[bold green]Contract saved to:[/bold green] {output_path}")
            
            # Save iteration data if requested
            if args.save_iterations:
                if args.iterations_output:
                    # Legacy path
                    iterations_path = args.iterations_output
                else:
                    # New path based on contract name
                    iterations_path = os.path.join(output_dir, f"{contract_name}_iterations")
                
                # Check if iteration files already exist
                if (os.path.exists(f"{iterations_path}.jsonl") or 
                    os.path.exists(f"{iterations_path}.json") or
                    os.path.exists(f"{iterations_path}_error_chart.html")):
                    # Only ask if we haven't already confirmed overwrite for the contract
                    if not os.path.exists(output_path) or args.iterations_output:
                        console.print(f"[bold yellow]Warning:[/bold yellow] Iteration files at {iterations_path} already exist.")
                        overwrite = input("Do you want to overwrite them? (y/N): ").strip().lower()
                        if overwrite != 'y':
                            console.print("[yellow]Skipped saving iteration data.[/yellow]")
                        else:
                            save_fine_tuning_data(fine_tuning_data, iterations_path, args.dark_mode)
                    else:
                        # We already confirmed overwrite for the output path
                        save_fine_tuning_data(fine_tuning_data, iterations_path, args.dark_mode)
                else:
                    save_fine_tuning_data(fine_tuning_data, iterations_path, args.dark_mode)
            
            # Generate test file if requested
            if args.generate_tests:
                console.print(f"[bold yellow]Note:[/bold yellow] Using default --save-dir='{args.save_dir}' to store test file.")
                # Automatically use the default save-dir
                try:
                    output_dir = args.save_dir
                    # Generate a name if not provided
                    if args.name:
                        contract_name = args.name
                    else:
                        # Create a name based on prompt and timestamp
                        prompt_part = args.prompt.split('.')[-1]  # Take the last part of the prompt path
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        contract_name = f"{prompt_part}_{timestamp}"
                    
                    # Determine test file path
                    if args.test_output:
                        test_output_path = args.test_output
                    else:
                        test_output_path = os.path.join(output_dir, f"{contract_name}_test.move")
                    
                    # Ensure the directory exists
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Check if test file already exists
                    if os.path.exists(test_output_path):
                        console.print(f"[bold yellow]Warning:[/bold yellow] Test file {test_output_path} already exists.")
                        overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
                        if overwrite != 'y':
                            console.print("[yellow]Skipped saving test file.[/yellow]")
                            return
                    
                    # Generate and save the test file
                    test_file_content = generate_test_file(final_contract, system_prompt)
                    with open(test_output_path, "w") as f:
                        f.write(test_file_content)
                    console.print(f"[bold green]Test file saved to:[/bold green] {test_output_path}")
                except Exception as e:
                    console.print(f"[bold red]Error generating test file:[/bold red] {e}")
        except Exception as e:
            console.print(f"[bold red]Error saving files:[/bold red] {e}")
    elif args.save_iterations:
        console.print("[bold yellow]Note:[/bold yellow] Using default --save-dir='{args.save_dir}' to store iteration data.")
        # Automatically use the default save-dir
        try:
            output_dir = args.save_dir
            # Generate a name if not provided
            if args.name:
                contract_name = args.name
            else:
                # Create a name based on prompt and timestamp
                prompt_part = args.prompt.split('.')[-1]  # Take the last part of the prompt path
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                contract_name = f"{prompt_part}_{timestamp}"
            
            # Full path for iterations
            iterations_path = os.path.join(output_dir, f"{contract_name}_iterations")
            
            # Ensure the directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Save the iterations data
            save_fine_tuning_data(fine_tuning_data, iterations_path, args.dark_mode)
        except Exception as e:
            console.print(f"[bold red]Error saving iteration data:[/bold red] {e}")
    elif args.generate_tests:
        console.print(f"[bold yellow]Note:[/bold yellow] Using default --save-dir='{args.save_dir}' to store test file.")
        # Automatically use the default save-dir
        try:
            output_dir = args.save_dir
            # Generate a name if not provided
            if args.name:
                contract_name = args.name
            else:
                # Create a name based on prompt and timestamp
                prompt_part = args.prompt.split('.')[-1]  # Take the last part of the prompt path
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                contract_name = f"{prompt_part}_{timestamp}"
            
            # Determine test file path
            if args.test_output:
                test_output_path = args.test_output
            else:
                test_output_path = os.path.join(output_dir, f"{contract_name}_test.move")
            
            # Ensure the directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Check if test file already exists
            if os.path.exists(test_output_path):
                console.print(f"[bold yellow]Warning:[/bold yellow] Test file {test_output_path} already exists.")
                overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
                if overwrite != 'y':
                    console.print("[yellow]Skipped saving test file.[/yellow]")
                    return
            
            # Generate and save the test file
            test_file_content = generate_test_file(final_contract, system_prompt)
            with open(test_output_path, "w") as f:
                f.write(test_file_content)
            console.print(f"[bold green]Test file saved to:[/bold green] {test_output_path}")
        except Exception as e:
            console.print(f"[bold red]Error generating test file:[/bold red] {e}")


if __name__ == "__main__":
    main() 