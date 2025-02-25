"""
Prompt Loader Utility

This module provides functions to load prompts from YAML files.
"""

import os
import yaml
from typing import Dict, Any, List, Optional


class PromptLoader:
    """
    Utility class for loading prompts from YAML files.
    """
    
    def __init__(self, prompts_dir: str = '/Users/kz/vcs/neuromansui/prompts'):
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
    
    def get_prompt(self, prompt_path: str) -> Optional[str]:
        """
        Get a prompt by its path in the format 'namespace.prompt_name'.
        
        Args:
            prompt_path: Path to the prompt in format 'namespace.prompt_name'
            
        Returns:
            The prompt content or None if not found
        """
        parts = prompt_path.split('.')
        
        if len(parts) != 2:
            raise ValueError("Prompt path should be in format 'namespace.prompt_name'")
        
        namespace, prompt_name = parts
        
        if namespace not in self.prompts:
            return None
        
        prompt_data = self.prompts[namespace].get(prompt_name)
        if prompt_data and 'content' in prompt_data:
            return prompt_data['content']
        
        return None
    
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