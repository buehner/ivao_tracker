FROM python:3.13-slim@sha256:f3614d98f38b0525d670f287b0474385952e28eb43016655dd003d0e28cf8652

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
