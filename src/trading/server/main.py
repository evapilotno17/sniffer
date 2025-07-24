from fastapi import FastAPI
from trading.server.polymarket.router import router
from prometheus_client import make_asgi_app

"""
    entry point to our backend
"""

app = FastAPI(title="Sniffer Control")
app.include_router(router)

# Prometheus at /metrics
app.mount("/metrics", make_asgi_app())
