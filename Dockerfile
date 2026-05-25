FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip install --no-cache-dir requests

# Copy MCP server — genecalc.py goes into scripts/ so its ../../data resolves correctly
COPY scripts/mcp_server.py /app/
COPY scripts/genecalc.py /app/scripts/

# Copy data files
COPY data/digeguigui.db /app/data/
COPY data/morphs_*.json /app/data/

# Container paths
ENV DB_PATH=/app/data/digeguigui.db
ENV GENECALC_PATH=/app/scripts/genecalc.py
ENV INFER_URL=http://127.0.0.1:3457/predict
ENV MCP_PORT=3458

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:3458/health')"

EXPOSE 3458

CMD ["python3", "mcp_server.py"]
