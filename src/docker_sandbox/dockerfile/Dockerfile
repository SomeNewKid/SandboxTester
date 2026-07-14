FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /opt/sandbox-tester

RUN apt-get update \
    && apt-get install --yes --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash sandbox

RUN python -m venv /opt/sandbox-tester/.venv

ENV PATH="/opt/sandbox-tester/.venv/bin:${PATH}"

COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir openai paramiko pillow playwright pymysql
