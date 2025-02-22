# Welcome to IVAO tracker

[![codecov](https://codecov.io/gh/buehner/ivao_tracker/branch/main/graph/badge.svg?token=ivao_tracker_token_here)](https://codecov.io/gh/buehner/ivao_tracker)
[![CI](https://github.com/buehner/ivao_tracker/actions/workflows/main.yml/badge.svg)](https://github.com/buehner/ivao_tracker/actions/workflows/main.yml)

This project started as a playground to learn the Python language.
The git repository has been generated with [this template](https://github.com/rochacbruno/python-project-template).

## Requirements

You need poetry.

## Setup

Install dependencies:

```bash
make install
```

Activate the virtual environment:
```bash
source $(poetry env info --path)/bin/activate
```

## Usage

Run the tests:

```bash
make test
```

Run the code:

```bash
python -m ivao_tracker
```

docker build -f Dockerfile -t ivao --progress=plain ..