"""
Adapter that lets the Flagsmith SDK behavioural spec drive this SDK.

Protocol: https://github.com/Flagsmith/sdk-spec/blob/main/ADAPTER.md
"""

import itertools
import json
import os
import re
import traceback
import typing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from flagsmith import Flagsmith
from flagsmith.models import Flags
from flagsmith.version import __version__

clients: typing.Dict[str, Flagsmith] = {}
client_ids = itertools.count(1)

CLIENT_ROUTE = re.compile(r"^/clients/(?P<client_id>[^/]+)(?P<action>/[a-z-]+)?$")


def serialise_flags(flags: Flags) -> typing.Dict[str, typing.Any]:
    return {
        "flags": [
            {"featureName": flag.feature_name, "enabled": flag.enabled, "value": flag.value}
            for flag in flags.all_flags()
        ]
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: typing.Any = None) -> None:
        payload = json.dumps(body).encode() if body is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _body(self) -> typing.Any:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else {}

    def _dispatch(self) -> None:
        try:
            self._route()
        except Exception as e:  # noqa: BLE001 - report SDK errors to the runner
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def _route(self) -> None:
        if self.command == "GET" and self.path == "/health":
            return self._send(200, {"sdk": "flagsmith-python-client", "version": __version__})

        if self.command == "POST" and self.path == "/clients":
            body = self._body()
            client_id = str(next(client_ids))
            clients[client_id] = Flagsmith(
                environment_key=body["environmentKey"],
                api_url=body["apiUrl"],
            )
            return self._send(201, {"clientId": client_id})

        match = CLIENT_ROUTE.match(self.path)
        if not match or match["client_id"] not in clients:
            return self._send(404, {"error": f"No route for {self.command} {self.path}"})
        client_id, action = match["client_id"], match["action"]

        if self.command == "DELETE" and action is None:
            del clients[client_id]
            return self._send(204)

        if self.command == "POST" and action == "/environment-flags":
            return self._send(200, serialise_flags(clients[client_id].get_environment_flags()))

        if self.command == "POST" and action == "/identity-flags":
            body = self._body()
            flags = clients[client_id].get_identity_flags(
                body["identifier"], traits=body.get("traits") or {}
            )
            return self._send(200, serialise_flags(flags))

        return self._send(404, {"error": f"No route for {self.command} {self.path}"})

    do_GET = do_POST = do_DELETE = _dispatch

    def log_message(self, format: str, *args: typing.Any) -> None:
        print(f"adapter: {format % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"adapter: listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
