from modules import script_callbacks

ALLOWED_ORIGINS = {
    "https://bighipadventure.github.io",
}
ALLOWED_METHODS = b"GET, POST, PUT, DELETE, OPTIONS"
PREFLIGHT_MAX_AGE = b"600"
PING_PATH = "/stillmange-cors/ping"
VERSION = "2"


class StillmangeCORS:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        origin = headers.get("origin")
        if origin not in ALLOWED_ORIGINS:
            await self.app(scope, receive, send)
            return
        cors = [
            (b"access-control-allow-origin", origin.encode("latin-1")),
            (b"access-control-allow-credentials", b"true"),
            (b"vary", b"Origin"),
        ]
        if scope["method"] == "OPTIONS" and "access-control-request-method" in headers:
            requested = headers.get("access-control-request-headers", "*").encode("latin-1")
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": cors + [
                    (b"access-control-allow-methods", ALLOWED_METHODS),
                    (b"access-control-allow-headers", requested),
                    (b"access-control-allow-private-network", b"true"),
                    (b"access-control-max-age", PREFLIGHT_MAX_AGE),
                    (b"content-length", b"0"),
                ],
            })
            await send({"type": "http.response.body", "body": b""})
            return
        names = {name for name, _ in cors}

        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                kept = [h for h in message.get("headers", []) if h[0].lower() not in names]
                message["headers"] = kept + cors
            await send(message)

        await self.app(scope, receive, send_with_cors)


def ping():
    return {"ok": True, "extension": "stillmange-cors", "version": VERSION, "allowed_origins": sorted(ALLOWED_ORIGINS)}


def on_app_started(demo, app):
    if getattr(app, "_stillmange_cors", False):
        return
    app._stillmange_cors = True
    app.add_api_route(PING_PATH, ping, methods=["GET"])
    build = app.build_middleware_stack
    app.build_middleware_stack = lambda: StillmangeCORS(build())
    app.middleware_stack = None
    print(f"[stillmange-cors] v{VERSION} allowed origins: {', '.join(sorted(ALLOWED_ORIGINS))}  check: {PING_PATH}")


script_callbacks.on_app_started(on_app_started)
