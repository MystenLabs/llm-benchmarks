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

# Download and install python 3.13
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get install -y python3.13
RUN ln -s /usr/bin/python3.13 /usr/bin/python3
RUN ln -s /usr/bin/python3.13 /usr/bin/python

# Copy requirements
COPY pyproject.toml poetry.lock* /app/

# Install Python dependencies
RUN pip3 install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy the application
COPY neuromansui /app/neuromansui
COPY prompts /app/prompts

# Setup the report server
COPY neuromansui-server /app/neuromansui-server
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
ENTRYPOINT ["python3", "-m", "neuromansui.main"]

# Default command
CMD ["--help"] 