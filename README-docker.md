# Neuromansui Docker & Kubernetes Setup

This documentation provides instructions for Dockerizing and deploying the Neuromansui application on Kubernetes.

## What is Neuromansui?

Neuromansui is a tool for compiling and iterative evaluation of Sui Move smart contracts using LLM-generated code. It uses OpenAI's API to generate and refine smart contracts, helping developers create robust Move code more efficiently.

## Docker Containerization

### Prerequisites

- Docker installed on your system
- OpenAI API key

### Building the Docker Image

1. Clone this repository or copy the Dockerfile and related files to your project directory.

2. Build the Docker image:

```bash
docker build -t neuromansui:latest .
```

3. Run the container locally:

```bash
docker run -it --rm \
  -e OPENAI_API_KEY=your_openai_api_key \
  -v "$(pwd)/outputs:/app/outputs" \
  neuromansui:latest \
  --prompt sui_move.base_contract \
  --save-dir /app/outputs \
  --generate-tests
```

Replace `your_openai_api_key` with your actual OpenAI API key.

### Docker Image Details

The Docker image:

- Is based on Ubuntu 22.04
- Includes Python 3 and all required Python dependencies
- Installs the Sui CLI for contract compilation
- Uses Poetry for Python dependency management
- Contains all required prompts for contract generation
- Fixes the hardcoded path in the prompt loader

## Kubernetes Deployment

For Kubernetes deployment instructions, see the `k8s/README.md` file.

### Quick Start

1. Build and push the Docker image to your container registry.
2. Update the image reference in `k8s/deployment.yaml` and `k8s/job.yaml`.
3. Create the necessary Kubernetes resources:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
```

## Configuration Options

The Neuromansui CLI supports the following options:

- `--prompt NAMESPACE.NAME`: The prompt to use for generation (e.g., sui_move.base_contract)
- `--module-name NAME`: Name of the module to generate
- `--max-iterations NUM`: Maximum number of refinement iterations
- `--save-dir DIR`: Directory to save output files
- `--generate-tests`: Generate test file for the contract
- `--save-iterations`: Save iteration data for fine-tuning
- `--dark-mode`: Use dark mode for visualizations

## Example: Generating an NFT Contract

```bash
docker run -it --rm \
  -e OPENAI_API_KEY=your_openai_api_key \
  -v "$(pwd)/outputs:/app/outputs" \
  neuromansui:latest \
  --prompt sui_move.nft_contract \
  --module-name my_nft \
  --save-dir /app/outputs \
  --generate-tests \
  --save-iterations
```

## Accessing Generated Contracts

When using Docker locally, mount a volume to the `/app/outputs` directory:

```bash
docker run -it --rm \
  -v "$(pwd)/outputs:/app/outputs" \
  ...
```

The generated contracts will be available in your local `outputs` directory.

## Troubleshooting

- **OpenAI API errors**: Ensure your API key is correct and has sufficient quota
- **Compilation errors**: These are expected as part of the iterative refinement process
- **Container resource issues**: For complex contracts, increase memory allocation to Docker or adjust Kubernetes resource limits

For more detailed information about the application itself, refer to the original README.md file. 