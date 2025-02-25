# neuroman.sui

> "Came a voice, out of the babel of tongues, speaking to us. It played us a mighty dub."     
> — William Gibson, Neuromancer

## Overview

`neuroman.sui` is a Python-based iterative evaluation pipeline that leverages OpenAI's GPT-4 to automatically generate and refine Sui Move smart contracts. The pipeline generates a contract from a given prompt, simulates a compilation step to capture errors, and then uses the compiler feedback to iteratively improve the contract until it meets a fixed specification.

## Goals

- **Iterative Refinement**: Automatically refines contract code based on simulated compiler feedback.
- **LLM Integration**: Uses OpenAI's GPT-4 to generate and improve smart contract code.
- **Prompt Library**: Includes a collection of YAML-based prompts for different contract types.
- **Extensible Pipeline**: Easily customizable for additional evaluation metrics or alternative compiler integrations.

## Installation

### Clone the Repository:

```bash
git clone https://github.com/MystenLabs/neuromansui.git
cd neuromansui
```

### Create a Virtual Environment (Optional but Recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install with Poetry:

```bash
poetry install
```

Key dependencies include:
- openai
- python-dotenv
- pyyaml

### Configure Environment Variables:

Create a `.env` file in the root directory and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### List Available Prompts:

```bash
poetry run python neuromansui/main.py --list
```

### Generate a Contract:

```bash
poetry run python neuromansui/main.py --prompt sui_move.base_contract
```

### Additional Options:

```bash
poetry run python neuromansui/main.py --prompt sui_move.nft_contract --max-iterations 10
```

The script will:
1. Generate an initial version of a Sui Move contract based on the selected prompt.
2. Simulate the compilation process and output compiler feedback.
3. Iteratively refine the contract code until it compiles successfully or reaches the maximum iterations.
4. Print the final contract source code to the console.

## Project Structure

```
neuromansui/
├── .env                   # Environment variables (e.g., OpenAI API key)
├── neuromansui/           # Main package directory
│   ├── main.py            # Main Python script implementing the evaluation pipeline
│   └── prompt_loader.py   # Utility for loading prompts from YAML files
├── prompts/               # YAML files containing prompts for different contract types
│   └── sui_move.yaml      # Sui Move contract prompts
├── pyproject.toml         # Poetry configuration and dependencies
├── setup.sh               # Setup script for quick installation and testing
└── README.md              # This file
```

## Customization

### Adding New Prompts:
Create or modify YAML files in the `prompts/` directory to add new contract templates or modify existing ones.

### Compiler Integration:
The `compile_contract` function in `main.py` currently simulates a compilation step. Replace this simulation with an actual call to the Sui Move compiler if needed.

### Iteration Settings:
Modify the `--max-iterations` parameter when running the script to control the number of refinement cycles.

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page if you want to contribute.

## License

This project is licensed under the MIT License. See the LICENSE file for details.


