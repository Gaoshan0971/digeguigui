FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy MCP server and dependencies
COPY scripts/mcp_server.py /app/
COPY data/digeguigui.db /app/data/

# Install Python deps
RUN pip install --no-cache-dir flask

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:3458/health')"

EXPOSE 3458

CMD ["python3", "mcp_server.py"]
