"""Presentation layer module.

HTTP and WebSocket handlers — the outermost ring of Clean Architecture.
- api/ — FastAPI route handlers (controllers)
- websockets/ — WebSocket handlers
- middleware/ — cross-cutting HTTP concerns

Controllers depend on application use cases (injected via FastAPI Depends).
"""

