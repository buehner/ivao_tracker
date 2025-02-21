FROM python:3.12-slim@sha256:34656cd90456349040784165b9decccbcee4de66f3ead0a1168ba893455afd1e
RUN apt-get update && \
    apt-upgrade -y && \
    apt-get install -y libpq-dev gcc

COPY . /app
WORKDIR /app

RUN pip install .
CMD ["ivao_tracker"]
