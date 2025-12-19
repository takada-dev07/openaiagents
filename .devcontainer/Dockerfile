FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    libreoffice \
    poppler-utils \
    fonts-noto-cjk \
    git \
    curl \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Create a non-root user compatible with VS Code Dev Containers.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash

WORKDIR /workspaces/openaiagents

USER $USERNAME


