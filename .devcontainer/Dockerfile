FROM mcr.microsoft.com/devcontainers/python:3.11

# Install MySQL client for CLI access
RUN apt-get update \
    && apt-get install -y --no-install-recommends mysql-client \
    && rm -rf /var/lib/apt/lists/*
