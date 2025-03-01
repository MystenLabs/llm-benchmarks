# neuroman.sui

> "Came a voice, out of the babel of tongues, speaking to us. It played us a mighty dub."     
> — William Gibson, Neuromancer

## Overview

`neuroman.sui` is a Python-based iterative evaluation pipeline that leverages OpenAI's GPT-4 to automatically generate and refine Sui Move smart contracts. The pipeline generates a contract from a given prompt, attempts to compile it, and then uses the compiler feedback to iteratively improve the contract until either it compiles successfully or the maximum number of iterations is reached.

## Components

- **Smart Contract Generator**: Core Python tool that uses LLMs to generate and refine Move code
- **Report Visualizer**: HTML-based visualizations of error progression during refinement
- **Report Server**: Web-based server for browsing and viewing generated reports and contracts

## Goals

- **Iterative Refinement**: Automatically refines contract code based on simulated compiler feedback.
- **LLM Integration**: Uses OpenAI's GPT-4 to generate and improve smart contract code.
- **Prompt Library**: Includes a collection of YAML-based prompts for different contract types.
- **Extensible Pipeline**: Easily customizable for additional evaluation metrics or alternative compiler integrations.

## Installation

### Clone the Repository:

```bash
git clone https://github.com/MystenLabs/gymnasuium.git
cd gymnasuium
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

### Command-Line Options

```
usage: python -m gymnasuium.main [-h] [--prompt PROMPT] [--list]
                                 [--max-iterations MAX_ITERATIONS]
                                 [--output OUTPUT] [--save-dir SAVE_DIR]
                                 [--name NAME] [--generate-tests]
                                 [--test-output TEST_OUTPUT]
                                 [--save-iterations]
                                 [--iterations-output ITERATIONS_OUTPUT]
                                 [--dark-mode]

Gymnasuium: LLM-powered Sui Move contract generator

options:
  -h, --help            show this help message and exit
  --prompt PROMPT       Prompt path to use (format: namespace.prompt_name)
  --list                List all available prompts
  --max-iterations MAX_ITERATIONS
                        Maximum number of iterations for refinement
  --output OUTPUT       Save the generated contract to this file path (deprecated, use --save-dir and --name instead)
  --save-dir SAVE_DIR   Directory to save all output files (defaults to 'test_outputs')
  --name NAME           Name for the output files (defaults to auto-generated from prompt name and timestamp)
  --generate-tests      Generate test file for the contract
  --test-output TEST_OUTPUT
                        Path to save the generated test file (defaults to contract_name_test.move)
  --save-iterations     Save all iteration data for fine-tuning
  --iterations-output ITERATIONS_OUTPUT
                        Path to save the iteration data (without extension, deprecated, use --save-dir and --name instead)
  --dark-mode           Use dark mode for visualizations
```

### Basic Examples

List available prompts:
```bash
python -m gymnasuium.main --list
```

Generate a basic Sui Move contract:
```bash
python -m gymnasuium.main --prompt sui_move.base_contract
```

Generate a contract and save it:
```bash
python -m gymnasuium.main --prompt sui_move.base_contract --save-dir my_contracts
```

Generate a contract with a specific name:
```bash
python -m gymnasuium.main --prompt sui_move.base_contract --save-dir my_contracts --name token_contract
```

Generate a contract and save iterations data for fine-tuning:
```bash
python -m gymnasuium.main --prompt sui_move.base_contract --save-dir my_contracts --name token_contract --save-iterations
```

Generate a contract with test file and visualizations:
```bash
python -m gymnasuium.main --prompt sui_move.base_contract --save-dir my_contracts --name token_contract --save-iterations --generate-tests --dark-mode
```

### Using the Report Server

The project includes a web-based server for viewing HTML reports:

```bash
# Start the report server
./start-server.sh
```

Then open your browser at http://localhost:3000 to access the dashboard.

### Docker Usage

Using Docker Compose:

```bash
# Run the standard generator
docker-compose up gymnasuium

# Run the report server
docker-compose up gymnasuium-server
```

## Available Contract Templates

The following contract templates are available:

- **sui_move.base_contract**: Basic token contract with mint, burn, and transfer functions
- **sui_move.nft_contract**: NFT collection contract with metadata management
- **sui_move.defi_contract**: Simple DeFi protocol with liquidity pools and swaps
- **sui_move.game_contract**: Advanced GameFi contract with character attributes, items, and game mechanics

## Project Structure

```
gymnasuium/
├── .env                   # Environment variables (e.g., OpenAI API key)
├── gymnasuium/           # Main package directory
│   ├── main.py            # Main Python script implementing the evaluation pipeline
│   └── prompt_loader.py   # Utility for loading prompts from YAML files
├── prompts/               # YAML files containing prompts for different contract types
│   └── sui_move.yaml      # Sui Move contract prompts
├── gymnasuium-server/    # Next.js web server for viewing reports
├── pyproject.toml         # Poetry configuration and dependencies
├── start-server.sh        # Script to start the report server
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

## Features

- **Iterative Refinement**: Automatically refines contract code based on compiler feedback
- **LLM Integration**: Uses OpenAI's LLM to generate and improve smart contract code
- **Prompt Library**: Includes a collection of YAML-based prompts for different contract types
- **Test Generation**: Automatically generates test files for the contracts
- **Progress Tracking**: Visual progress indicators and metrics during refinement
- **File Output**: Save contracts and tests to specified file paths
- **Fine-tuning Data Collection**: Save iteration data in formats suitable for fine-tuning language models
- **Detailed Error Reporting**: Structured error reports with categorization and statistics
- **Extensible Pipeline**: Easily customizable for additional evaluation metrics
- **Visualization**: Interactive Plotly charts for error progression
- **Report Server**: Web-based interface for browsing and viewing generated reports

## Visualization Features

- Stacked bar chart showing errors by type for each iteration
- Trend line showing total errors over iterations
- Percentage improvement annotations between iterations
- Interactive tooltips with detailed error information
- Star markers indicating successful compilations
- Automatic generation of both light and dark mode versions


