FROM python:3.12-slim@sha256:86cd49938a9b50c3663aa93cf5db9c8f498d6fe47f463a2cb967248b9e7d69de
RUN apt-get update && \
    apt-get install -y libpq-dev gcc

COPY . /app
WORKDIR /app

RUN pip install .
CMD ["ivao_tracker"]
