"""SQLAlchemy ORM models for the PageIndex RAG application.

All tables use the ``rag_`` prefix so they can coexist with Open WebUI
tables in the same PostgreSQL database without naming collisions.

Models
------
Workspace
    A named collection of documents owned by a single user.
Document
    Metadata for a processed document that lives inside a workspace.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


class Workspace(Base):
    """A named workspace owned by a user, containing zero or more documents."""

    __tablename__ = "rag_workspaces"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=False, default="", server_default="")
    owner_username: str = Column(String(255), nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    documents = relationship(
        "Document",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ------------------------------------------------------------------
    # Constraints & indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        UniqueConstraint("owner_username", "name", name="uq_workspace_owner_name"),
        Index("idx_workspaces_owner", "owner_username"),
    )

    def __repr__(self) -> str:
        return (
            f"<Workspace(id={self.id}, name={self.name!r}, "
            f"owner={self.owner_username!r})>"
        )


class Document(Base):
    """Metadata for a single processed document within a workspace."""

    __tablename__ = "rag_documents"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id: int = Column(
        Integer,
        ForeignKey("rag_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    username: str = Column(String(255), nullable=False)
    file_name: str = Column(String(512), nullable=False)
    file_hash: str = Column(String(128), nullable=False)
    file_size: int = Column(Integer, nullable=False, default=0, server_default="0")
    doc_title: str = Column(String(512), nullable=False, default="", server_default="")
    root_summary: str = Column(Text, nullable=False, default="", server_default="")
    node_count: int = Column(Integer, nullable=False, default=0, server_default="0")
    image_count: int = Column(Integer, nullable=False, default=0, server_default="0")
    page_count: int = Column(Integer, nullable=False, default=0, server_default="0")
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    workspace = relationship("Workspace", back_populates="documents")

    # ------------------------------------------------------------------
    # Constraints & indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "file_hash", name="uq_document_workspace_hash"
        ),
        Index("idx_documents_workspace", "workspace_id"),
        Index("idx_documents_username", "username"),
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, file_name={self.file_name!r}, "
            f"workspace_id={self.workspace_id})>"
        )
