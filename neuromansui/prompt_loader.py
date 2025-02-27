"""
Prompt Loader Utility

This module provides functions to load prompts from YAML files.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
import json
import re
from collections import defaultdict


class PromptLoader:
    """
    Utility class for loading prompts from YAML files.
    """
    
    def __init__(self, prompts_dir: str = 'prompts'):
        """
        Initialize the PromptLoader with the directory containing prompt files.
        
        Args:
            prompts_dir: Path to the directory containing prompt YAML files
        """
        self.prompts_dir = prompts_dir
        self.prompts = {}
        self._load_all_prompts()
    
    def _load_all_prompts(self) -> None:
        """
        Load all prompt files from the prompts directory.
        """
        if not os.path.exists(self.prompts_dir):
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
        
        for filename in os.listdir(self.prompts_dir):
            if filename.endswith(('.yaml', '.yml')):
                file_path = os.path.join(self.prompts_dir, filename)
                namespace = os.path.splitext(filename)[0]
                
                try:
                    with open(file_path, 'r') as file:
                        prompt_data = yaml.safe_load(file)
                        
                    # Store prompts under their namespace
                    if prompt_data:
                        self.prompts[namespace] = prompt_data
                except Exception as e:
                    print(f"Error loading prompt file {file_path}: {e}")
    
    def get_prompt(self, prompt_path: str) -> tuple[Optional[str], Optional[str]]:
        """
        Get a prompt by its path in the format 'namespace.prompt_name'.
        
        Args:
            prompt_path: Path to the prompt in format 'namespace.prompt_name'
            
        Returns:
            Tuple of (prompt content, system prompt) or (None, None) if not found
        """
        parts = prompt_path.split('.')
        
        if len(parts) != 2:
            raise ValueError("Prompt path should be in format 'namespace.prompt_name'")
        
        namespace, prompt_name = parts
        
        if namespace not in self.prompts:
            return None, None
        
        prompt_data = self.prompts[namespace].get(prompt_name)
        if not prompt_data:
            return None, None
        
        content = prompt_data.get('content')
        system_prompt = prompt_data.get('system_prompt', "You are an expert in Sui Move smart contract development.")
        
        return content, system_prompt
    
    def list_prompts(self) -> List[str]:
        """
        List all available prompts.
        
        Returns:
            List of prompt paths in format 'namespace.prompt_name'
        """
        result = []
        for namespace, prompts in self.prompts.items():
            for prompt_name in prompts.keys():
                result.append(f"{namespace}.{prompt_name}")
        return result
    
    def get_prompt_description(self, prompt_path: str) -> Optional[str]:
        """
        Get the description for a prompt.
        
        Args:
            prompt_path: Path to the prompt in format 'namespace.prompt_name'
            
        Returns:
            The prompt description or None if not found
        """
        parts = prompt_path.split('.')
        
        if len(parts) != 2:
            raise ValueError("Prompt path should be in format 'namespace.prompt_name'")
        
        namespace, prompt_name = parts
        
        if namespace not in self.prompts:
            return None
        
        prompt_data = self.prompts[namespace].get(prompt_name)
        if prompt_data and 'description' in prompt_data:
            return prompt_data['description']
        
        return None

def compute_error_code(error: dict) -> str:
    """
    Compute a standardized error code for an error object.

    The error code is built as follows:
      - Determine a severity prefix using the error's "level":
          • "BlockingError" or "NonblockingError" → "E" for Error, "N" for NonblockingError
          • "Warning" → "W"
          • "Note" → "I"
          • "Bug" → "ICE"
          • Otherwise, use the first letter of the level (if available)
      - Add the error code padded to 2 digits
      - Add the category padded to 3 digits
      - If an "external_prefix" exists, prepend it to the result.

    Args:
        error: A dictionary with keys "level", "code", "category", and optionally "external_prefix".

    Returns:
        A formatted error code string.
    """
    level = error.get("level", "")
    code_val = error.get("code")
    category_val = error.get("category")
    external_prefix = error.get("external_prefix")

    match level:
        case "BlockingError":
            sev_prefix = "E"
        case "NonblockingError":
            sev_prefix = "N"
        case "Warning":
            sev_prefix = "W"
        case "Note":
            sev_prefix = "I"
        case "Bug":
            sev_prefix = "ICE"
        case "Error":
            sev_prefix = "E"
        case _:
            sev_prefix = level[0] if level else ""

    # Format code as code then category (instead of category then code)
    # Pad code to 2 digits and category to 3 digits
    code_str = str(code_val).zfill(2)
    cat_str = str(category_val).zfill(3)

    # Special handling for linter warnings (code 4)
    if code_val == 4 and level == "Warning":
        return f"Lint {sev_prefix}{code_str}{cat_str}"

    if external_prefix:
        return f"{external_prefix}{sev_prefix}{code_str}{cat_str}"
    return f"{sev_prefix}{code_str}{cat_str}"

def collect_errors(compiler_output: str) -> dict[str, list[dict]]:
    """
    Extract error objects from the compiler output and group them by a computed error code.

    This function looks for a JSON array of error objects within the compiler output,
    parses it, computes an error code for each error using `compute_error_code`,
    and groups the errors in a dictionary keyed by those computed codes.

    Args:
        compiler_output: A string containing the compiler output, including a JSON array of errors.

    Returns:
        A dictionary mapping computed error codes to lists of error dictionaries.
    """
    match_obj = re.search(r"(\[.*?\])", compiler_output, re.DOTALL)
    if not match_obj:
        raise ValueError("No JSON array found in the compiler output.")
    
    json_str = match_obj.group(1)
    try:
        errors_list = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON: {e}")
    
    grouped_errors = defaultdict(list)
    for error in errors_list:
        error_code = compute_error_code(error)
        grouped_errors[error_code].append(error)
    
    return dict(grouped_errors)
