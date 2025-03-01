FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.cargo/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3 \
    python3-pip \
    python3-dev \
    pkg-config \
    libssl-dev \
    libclang-dev \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Download the Sui CLI
RUN curl -fsSL https://github.com/MystenLabs/sui/releases/download/mainnet-v1.43.1/sui-mainnet-v1.43.1-ubuntu-aarch64.tgz -o /usr/local/bin/sui.tgz
RUN tar -xzf /usr/local/bin/sui.tgz -C /usr/local/bin
RUN rm /usr/local/bin/sui.tgz
# add sui to PATH
ENV PATH="/usr/local/bin:/usr/local/bin/sui:${PATH}"

# Install Node.js for the report server
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    node --version && \
    npm --version

# Set up Python environment
WORKDIR /app

# Download and install Python 3.12 (more stable than 3.13)
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get install -y python3.12 python3.12-venv
# Update Python symlinks (removing existing ones first)
RUN rm -f /usr/bin/python3 && ln -s /usr/bin/python3.12 /usr/bin/python3
RUN rm -f /usr/bin/python && ln -s /usr/bin/python3.12 /usr/bin/python

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Copy requirements
COPY pyproject.toml poetry.lock* README.md /app/
# Copy the application
COPY neuromansui /app/neuromansui
COPY neuromansui-server /app/neuromansui-server
COPY test_outputs /app/test_outputs
COPY prompts /app/prompts

WORKDIR /app/neuromansui

# Install Python dependencies
RUN python3 -m pip install poetry && \
    poetry lock && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-root --no-ansi

WORKDIR /app/neuromansui-server
RUN npm install && \
    npm run build
WORKDIR /app

# Fix the prompt_loader.py to use relative path
COPY fix_paths.sh /app/
RUN chmod +x /app/fix_paths.sh
RUN /app/fix_paths.sh

# Create output directories
RUN mkdir -p /app/test_outputs /app/outputs

# Copy the start script
COPY start-server.sh /app/
RUN chmod +x /app/start-server.sh

# Set the entry point
WORKDIR /app
ENTRYPOINT ["npm", "run", "dev"]

# Default command
CMD ["--help"]