"""Receptor LOCAL de alertas (webhook do Alertmanager), só para teste. Não envia nada para fora.

POST /alertas  guarda o que o Alertmanager entregou (e imprime uma linha por alerta no log)
GET  /alertas  devolve tudo que chegou, em JSON
GET  /saude    responde ok
"""

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

RECEBIDOS: list[dict] = []


class Receptor(BaseHTTPRequestHandler):
    def _responder(self, codigo: int, corpo: bytes, tipo: str = "application/json") -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/saude":
            self._responder(200, b"ok", "text/plain")
        elif self.path == "/alertas":
            self._responder(200, json.dumps(RECEBIDOS, ensure_ascii=False).encode())
        else:
            self._responder(404, b"{}")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/alertas":
            self._responder(404, b"{}")
            return
        pacote = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        for alerta in pacote.get("alerts", []):
            registro = {
                "recebido_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "estado": alerta.get("status"),
                "alerta": alerta.get("labels", {}).get("alertname"),
                "fila": alerta.get("labels", {}).get("queue"),
                "gravidade": alerta.get("labels", {}).get("severity"),
                "resumo": alerta.get("annotations", {}).get("summary"),
            }
            RECEBIDOS.append(registro)
            print(json.dumps(registro, ensure_ascii=False), flush=True)
        self._responder(200, b"{}")

    def log_message(self, *_args) -> None:  # silencia o log de acesso padrão
        pass


if __name__ == "__main__":
    print("receptor de alertas de teste em :8080", file=sys.stderr, flush=True)
    HTTPServer(("0.0.0.0", 8080), Receptor).serve_forever()  # noqa: S104 (rede interna do Compose)
