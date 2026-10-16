"""Small local-demo request boundary; not a public authentication system."""

from starlette.responses import JSONResponse


class RequestGuards:
    def __init__(self, app, max_body=32768):
        self.app = app
        self.max_body = max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {
            k.decode("latin1").lower(): v.decode("latin1") for k, v in scope["headers"]
        }

        async def reject(code, message):
            await JSONResponse({"error": message}, status_code=code)(
                scope, receive, send
            )

        if (
            len(headers.get("range", "")) > 1024
            or headers.get("range", "").count(",") > 16
        ):
            return await reject(400, "Range header exceeds the supported limit")
        if scope["method"] in ("POST", "PUT", "PATCH", "DELETE"):
            if headers.get("sec-fetch-site") == "cross-site":
                return await reject(403, "Cross-site mutation refused")
            if headers.get("content-encoding", "identity").lower() != "identity":
                return await reject(415, "Encoded request bodies are not supported")
            size = headers.get("content-length")
            if size:
                try:
                    declared = int(size)
                except ValueError:
                    return await reject(400, "Invalid Content-Length")
                if declared < 0:
                    return await reject(400, "Invalid Content-Length")
                if declared > self.max_body:
                    return await reject(413, "Request exceeds the 32KB limit")
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > self.max_body:
                    return await reject(413, "Request exceeds the 32KB limit")
                if not message.get("more_body", False):
                    break
            if (
                body
                and headers.get("content-type", "").split(";")[0].strip().lower()
                != "application/json"
            ):
                return await reject(415, "Mutations require application/json")
            delivered = False
            original_receive = receive

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {
                        "type": "http.request",
                        "body": bytes(body),
                        "more_body": False,
                    }
                return await original_receive()

            receive = replay
        await self.app(scope, receive, send)
