FROM python:3.13-slim@sha256:ae9f9ac89467077ed1efefb6d9042132d28134ba201b2820227d46c9effd3174
RUN apt-get update && \
    apt-upgrade -y && \
    apt-get install -y libpq-dev gcc

COPY . /app
WORKDIR /app

RUN pip install .
CMD ["ivao_tracker"]
