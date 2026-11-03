import hashlib
import os
import socket
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

MAX_WORK = int(os.environ.get('MAX_WORK', '1000000'))
DEFAULT_WORK = int(os.environ.get('DEFAULT_WORK', '200000'))
INSTANCE = os.environ.get('INSTANCE_ID') or socket.gethostname()
SERVICE_ROLE = os.environ.get('SERVICE_ROLE', 'unified-monolith')

@app.get('/health')
def health():
    return jsonify(status='ok', service=SERVICE_ROLE, instance=INSTANCE), 200

@app.get('/status')
def status():
    return jsonify(
        status='Listing available',
        service=SERVICE_ROLE,
        instance=INSTANCE
    )

@app.get('/work')
def work():
    try:
        n = int(request.args.get('n', DEFAULT_WORK))
    except ValueError:
        n = DEFAULT_WORK
    n = max(1, min(n, MAX_WORK))
    start = time.perf_counter()
    h = b'abnb-poc'
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    work_ms = round((time.perf_counter() - start) * 1000, 1)
    return jsonify(
        status='done',
        service=SERVICE_ROLE,
        iterations=n,
        work_ms=work_ms,
        instance=INSTANCE
    )

# Airbnb SOA specific endpoints

@app.get('/listings')
def listings():
    """
    Lightweight I/O-style Presentation/Data Service endpoint.
    Fetches static property details (uses almost 0% CPU).
    """
    return jsonify(
        service='airbnb-listing-catalog-service',
        role=SERVICE_ROLE,
        instance=INSTANCE,
        listings=[
            {"id": "abnb-goa-101", "title": "Goa Beachfront Villa", "base_price_inr": 8500},
            {"id": "abnb-manali-202", "title": "Manali Snow Chalet", "base_price_inr": 6200},
            {"id": "abnb-udaipur-303", "title": "Udaipur Lakeview Suite", "base_price_inr": 11000}
        ]
    )

@app.get('/search-pricing')
def search_pricing():
    """
    CPU-Intensive Derived-Data Service endpoint.
    Simulates Airbnb's dynamic holiday surge-pricing & ranking calculation.
    """
    try:
        n = int(request.args.get('n', DEFAULT_WORK))
    except ValueError:
        n = DEFAULT_WORK
    n = max(1, min(n, MAX_WORK))
    start = time.perf_counter()
    h = b'abnb-holiday-pricing'
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    work_ms = round((time.perf_counter() - start) * 1000, 1)
    return jsonify(
        service='airbnb-dynamic-pricing-service',
        role=SERVICE_ROLE,
        holiday_season='Dec-Jan Peak Rush',
        surge_multiplier=1.85,
        recommended_listing='Goa Beachfront Villa',
        computed_nightly_rate_inr=int(8500 * 1.85),
        iterations=n,
        work_ms=work_ms,
        instance=INSTANCE
    )