"""Database layer for the PageIndex RAG FastAPI backend.

Provides SQLAlchemy ORM models, session management, and CRUD repository
classes for workspaces and documents. All tables are prefixed with ``rag_``
to coexist safely with Open WebUI tables in the same PostgreSQL database.
"""
