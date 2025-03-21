FROM python:3.13-slim@sha256:8f3aba466a471c0ab903dbd7cb979abd4bda370b04789d25440cc90372b50e04

SHELL ["/bin/bash", "-c"]

# Set poetry environment variables
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl libpq-dev build-essential postgresql-client && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get remove -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN pg_config --version

COPY ./README.md /ivao_tracker/README.md
COPY ./config.toml /ivao_tracker/config.toml
COPY ./pyproject.toml /ivao_tracker/pyproject.toml
COPY ./Makefile /ivao_tracker/Makefile
COPY ./ivao_tracker/ /ivao_tracker/ivao_tracker

RUN rm -Rf /ivao_tracker/ivao_tracker/__pycache__

WORKDIR /ivao_tracker

RUN python --version
RUN poetry --version
RUN poetry lock
RUN make install

CMD ["ivao_tracker"]
