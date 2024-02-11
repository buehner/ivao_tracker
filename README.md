
# ivao_tracker

[![codecov](https://codecov.io/gh/buehner/ivao_tracker/branch/main/graph/badge.svg?token=ivao_tracker_token_here)](https://codecov.io/gh/buehner/ivao_tracker)
[![CI](https://github.com/buehner/ivao_tracker/actions/workflows/main.yml/badge.svg)](https://github.com/buehner/ivao_tracker/actions/workflows/main.yml)

## Usage

Install requirements (once):
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

Run the tests:

```bash
$ python -m pytest
```

Run the code:

```bash
$ python -m ivao_tracker
```

Install the application:
```bash
$ pip install .
```

## The Makefile

All the utilities for the template and project are on the Makefile

```bash
❯ make
Usage: make <target>

Targets:
help:             ## Show the help.
install:          ## Install the project in dev mode.
fmt:              ## Format code using black & isort.
lint:             ## Run pep8, black, mypy linters.
test: lint        ## Run tests and generate coverage report.
watch:            ## Run tests on every change.
clean:            ## Clean unused files.
virtualenv:       ## Create a virtual environment.
release:          ## Create a new tag for release.
docs:             ## Build the documentation.
switch-to-poetry: ## Switch to poetry package manager.
```

## Development

Read the [CONTRIBUTING.md](CONTRIBUTING.md) file.
