import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _http import JsonHandler  # noqa: E402
from sinal_core import rank  # noqa: E402


def process(payload):
    items = payload.get("items", [])[:200]
    interests = payload.get("interests", [])
    ranked = rank(items, interests)
    min_score = int(payload.get("min_score", 0))
    top = int(payload.get("top", 0)) or len(ranked)
    kept = [r for r in ranked if r["score"] >= min_score][:top]
    return {"items": kept, "total": len(ranked), "kept": len(kept), "skipped": len(ranked) - len(kept)}


class handler(JsonHandler, BaseHTTPRequestHandler):
    process = staticmethod(process)
