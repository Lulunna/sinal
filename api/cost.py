import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _http import JsonHandler  # noqa: E402
from sinal_core import estimate_cost  # noqa: E402


def process(payload):
    # várias chamadas de uma vez: {"calls":[{"model","input_tokens","output_tokens"}, ...]}
    if isinstance(payload.get("calls"), list):
        costs = [estimate_cost(c.get("model", ""), c.get("input_tokens"), c.get("output_tokens"))["cost_usd"]
                 for c in payload["calls"][:20] if isinstance(c, dict)]
        return {"costs": costs, "total": round(sum(costs), 6)}
    return estimate_cost(payload.get("model", ""), payload.get("input_tokens", 0), payload.get("output_tokens", 0))


class handler(JsonHandler, BaseHTTPRequestHandler):
    process = staticmethod(process)
