FROM python:3.12-slim

LABEL org.opencontainers.image.title="ProxyWatch"
LABEL org.opencontainers.image.description="Real-Time SOCKS5 Proxy Monitoring Dashboard"
LABEL org.opencontainers.image.version="1.0.0"

# Install system dependencies for psutil and procfs access
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        procps \
        net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY proxywatch/ proxywatch/
COPY main.py .
COPY config.yaml .

# ProxyWatch needs access to:
#   - /proc/net/tcp, /proc/net/tcp6  (connection tracking)
#   - /proc/net/dev                   (bandwidth)
#   - /sys/class/net/*/statistics     (interface counters)
#   - /var/run/docker.sock            (Docker API)
# Run with: --pid=host --net=host -v /var/run/docker.sock:/var/run/docker.sock

ENTRYPOINT ["python", "main.py"]