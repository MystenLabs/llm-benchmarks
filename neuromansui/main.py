"""
Main application module for Neuromansui.

This module provides functionality for compiling and iterative evaluation of 
Sui Move smart contracts using LLM-generated code.
"""

import os
import subprocess
import time
import argparse
from dotenv import load_dotenv
import openai
from prompt_loader import PromptLoader

load_dotenv()

client = openai.OpenAI()

def compile_contract(contract_source: str) -> str:
    """
    Simulates compiling a Sui Move contract.
    Replace this function with an actual subprocess call to the Sui Move compiler.
    
    Args:
        contract_source: Source code of the contract to compile
        
    Returns:
        Compilation output message
    """
    # TODO: Replace with actual compiler call
    if "error" in contract_source.lower():
        return "Compilation Error: ability constraint not satisfied"
    else:
        return "Compilation Successful"

def generate_contract(prompt: str) -> str:
    """
    Use OpenAI API to generate contract code.
    
    Args:
        prompt: The prompt to send to the model
        
    Returns:
        Generated contract source code
    """
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You are an expert in Sui Move smart contract development."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def iterative_evaluation(base_prompt: str, max_iterations: int = 5) -> str:
    """
    Iteratively calls the LLM to refine the contract source code.
    
    Args:
        base_prompt: The base prompt to use for generation
        max_iterations: Maximum number of iterations to perform
        
    Returns:
        Final contract source code
    """
    feedback = "Initial run"  
    contract_source = ""
    
    for i in range(max_iterations):
        print(f"=== Iteration {i+1} ===")
        
        # Prepare the full prompt with feedback
        full_prompt = f"{base_prompt}\n\nFeedback: {feedback}"
        
        # Generate new contract source based on current feedback
        contract_source = generate_contract(full_prompt)
        print("Generated contract source:")
        print(contract_source)
        
        # Compile the contract and get compiler feedback
        compiler_feedback = compile_contract(contract_source)
        print("Compiler feedback:")
        print(compiler_feedback)
        
        # Check if compilation was successful
        if "Successful" in compiler_feedback:
            print("Contract compiled successfully.")
            break
        else:
            # Prepare new feedback incorporating the compiler errors
            feedback = (
                f"The contract did not compile. Compiler output: {compiler_feedback}. "
                "Please revise the contract accordingly, ensuring that all errors are resolved."
            )
            # Pause briefly before the next iteration
            time.sleep(1)
    
    return contract_source

def list_available_prompts(prompt_loader: PromptLoader) -> None:
    """
    List all available prompts with descriptions.
    
    Args:
        prompt_loader: The prompt loader instance
    """
    print("Available prompts:")
    print("------------------")
    
    for prompt_path in prompt_loader.list_prompts():
        description = prompt_loader.get_prompt_description(prompt_path)
        print(f"- {prompt_path}: {description}")
    print()

def main():
    """
    Main entry point for the application.
    """
    parser = argparse.ArgumentParser(description='Neuromansui: LLM-powered Sui Move contract generator')
    parser.add_argument('--prompt', type=str, default='sui_move.base_contract',
                        help='Prompt path to use (format: namespace.prompt_name)')
    parser.add_argument('--list', action='store_true',
                        help='List all available prompts')
    parser.add_argument('--max-iterations', type=int, default=5,
                        help='Maximum number of iterations for refinement')
    
    args = parser.parse_args()
    
    # Initialize prompt loader
    prompt_loader = PromptLoader()
    
    # List prompts if requested
    if args.list:
        list_available_prompts(prompt_loader)
        return
    
    # Get the specified prompt
    prompt_content = prompt_loader.get_prompt(args.prompt)
    
    if not prompt_content:
        print(f"Error: Prompt '{args.prompt}' not found.")
        list_available_prompts(prompt_loader)
        return
    
    print(f"Using prompt: {args.prompt}")
    print(f"Description: {prompt_loader.get_prompt_description(args.prompt)}")
    
    # Run iterative evaluation with the selected prompt
    final_contract = iterative_evaluation(base_prompt=prompt_content, max_iterations=args.max_iterations)
    
    print("=== Final contract source ===")
    print(final_contract)
    

if __name__ == "__main__":
    main() 