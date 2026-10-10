FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

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
