"""
FIX 5: Add rate limiting to webhook endpoints

CHECK first: Look at main.py to see what web framework is used.
Common patterns in this project:

A) If using Fastify (Node.js style) - already has @fastify/rate-limit
B) If using Python Flask/FastAPI:

FOR FLASK (most likely based on Python):
Add this to main.py or create middleware:

from flask import Flask, request, jsonify
from functools import wraps
import time

# Simple in-memory rate limiter for webhooks
WEBHOOK_RATE_LIMIT = {
    "binance_pay": {"max_calls": 10, "window_sec": 60},
}

webhook_call_history = {}

def rate_limit_webhook(endpoint_name: str, config: dict):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr or "unknown"
            key = f"{endpoint_name}:{client_ip}"
            now = time.time()
            
            if key not in webhook_call_history:
                webhook_call_history[key] = []
            
            # Clean old calls outside window
            webhook_call_history[key] = [
                t for t in webhook_call_history[key]
                if now - t < config["window_sec"]
            ]
            
            if len(webhook_call_history[key]) >= config["max_calls"]:
                return jsonify({"error": "rate_limit_exceeded", "retry_after": config["window_sec"]}), 429
            
            webhook_call_history[key].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

# USAGE on webhook route:
@app.route('/webhook/binance-pay', methods=['POST'])
@rate_limit_webhook('binance_pay', WEBHOOK_RATE_LIMIT["binance_pay"])
def binance_pay_webhook():
    # ... existing code

FOR MORE PRODUCTION: Use Redis-backed rate limiting with:
  from flask_limiter import Limiter
  limiter = Limiter(app, uri_mode="...) 
  @limiter.limit("10 per minute")
"""
