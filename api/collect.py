import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _http import JsonHandler  # noqa: E402
from sinal_core import collect  # noqa: E402


def process(payload):
    return collect(payload)


class handler(JsonHandler, BaseHTTPRequestHandler):
    process = staticmethod(process)
