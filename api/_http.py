"""Base comum das funções da Vercel: lê JSON, confere a chave, responde JSON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

MAX_BODY = 1_000_000


class JsonHandler:
    needs_key = True
    process = None

    def _send(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        expected = os.environ.get("SINAL_API_KEY", "")
        if not self.needs_key:
            return True
        return bool(expected) and self.headers.get("x-sinal-key", "") == expected

    def do_POST(self):
        if not self._authorized():
            return self._send(401, {"error": "chave inválida"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > MAX_BODY:
                return self._send(413, {"error": "pedido grande demais"})
            payload = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(payload, dict):
                return self._send(400, {"error": "o corpo precisa ser um objeto JSON"})
            return self._send(200, type(self).process(payload))
        except json.JSONDecodeError:
            return self._send(400, {"error": "JSON inválido"})
        except Exception as e:  # nunca devolve detalhes internos
            print("erro:", type(e).__name__, e)
            return self._send(500, {"error": "erro interno"})

    def do_GET(self):
        return self._send(200, {"ok": True})

    def log_message(self, *args):
        pass
