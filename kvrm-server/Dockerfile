FROM python:3.12-slim

WORKDIR /app
COPY kvrm-core/ kvrm-core/
COPY kvrm-server/ kvrm-server/
RUN pip install --no-cache-dir ./kvrm-core ./kvrm-server

ENV KVRM_SERVER_DATA=/data
VOLUME /data
EXPOSE 8000

# Set KVRM_API_KEYS in the environment for authenticated deployments.
CMD ["uvicorn", "kvrm_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
