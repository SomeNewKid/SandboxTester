FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

ARG SANDBOX_MINIMIZE_IMAGE=false

WORKDIR /opt/sandbox-tester

RUN apt-get update \
    && apt-get install --yes --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash sandbox

RUN python -m venv /opt/sandbox-tester/.venv

ENV PATH="/opt/sandbox-tester/.venv/bin:${PATH}"

COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir openai paramiko pillow playwright pymysql

RUN if [ "${SANDBOX_MINIMIZE_IMAGE}" = "true" ]; then \
        apt-get update \
        && apt-get purge --yes --auto-remove \
            git \
            gnupg \
            gpg \
            gpg-agent \
            openssh-client \
            perl \
        || true; \
        rm -f \
            /opt/sandbox-tester/.venv/bin/pip \
            /opt/sandbox-tester/.venv/bin/pip3 \
            /usr/bin/apt \
            /usr/bin/apt-get \
            /usr/bin/bash \
            /usr/bin/busctl \
            /usr/bin/dbus-send \
            /usr/bin/dpkg \
            /usr/bin/dpkg-query \
            /usr/bin/findmnt \
            /usr/bin/git \
            /usr/bin/gpg \
            /usr/bin/gpg-connect-agent \
            /usr/bin/gpgconf \
            /usr/bin/journalctl \
            /usr/bin/loginctl \
            /usr/bin/mount \
            /usr/bin/nice \
            /usr/bin/nohup \
            /usr/bin/nsenter \
            /usr/bin/perl \
            /usr/bin/renice \
            /usr/bin/scp \
            /usr/bin/sftp \
            /usr/bin/setsid \
            /usr/bin/ssh \
            /usr/bin/ssh-add \
            /usr/bin/su \
            /usr/bin/systemd-run \
            /usr/bin/systemctl \
            /usr/bin/umount \
            /usr/bin/unshare \
            /usr/sbin/service; \
        rm -rf /var/lib/apt/lists/* /var/cache/apt/*; \
    fi
