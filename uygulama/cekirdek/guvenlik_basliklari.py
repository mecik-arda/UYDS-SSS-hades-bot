from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class GuvenlikBasliklariMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, istek: Request, cagri_yoneticisi):
        yanit = await cagri_yoneticisi(istek)
        yanit.headers["X-Frame-Options"] = "DENY"
        yanit.headers["X-Content-Type-Options"] = "nosniff"
        yanit.headers["X-XSS-Protection"] = "1; mode=block"
        yanit.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        yanit.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        yanit.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'"
        yanit.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        yanit.headers["Cache-Control"] = "no-store, max-age=0"
        return yanit
