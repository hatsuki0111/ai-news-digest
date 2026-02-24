FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY ai_news_digest/ ai_news_digest/

RUN pip install --no-cache-dir .

ENV DIGEST_CONFIG=/app/config.yaml
ENV DIGEST_DATA_DIR=/app/data
ENV DIGEST_OUTPUT_DIR=/app/output

VOLUME ["/app/output", "/app/data"]

ENTRYPOINT ["ai-news-digest"]
CMD ["--hours", "24"]
