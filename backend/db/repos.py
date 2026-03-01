"""CRUD repository classes for Workspace and Document models.

Each repository exposes **static methods** that accept a SQLAlchemy
:class:`~sqlalchemy.orm.Session` as their first argument.  This keeps the
database logic decoupled from the FastAPI dependency-injection layer and
makes the functions easy to test or call from scripts.

All queries follow the **SQLAlchemy 2.0** style — ``session.execute(select(…))``
rather than the legacy ``session.query(…)`` approach.
"""

from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend.db.models import Document, Workspace


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------
class WorkspaceRepo:
    """Data-access helpers for the :class:`Workspace` model."""

    @staticmethod
    def create(
        session: Session,
        name: str,
        owner_username: str,
        description: str = "",
    ) -> Workspace:
        """Insert a new workspace and return the persisted instance.

        Parameters
        ----------
        session:
            Active SQLAlchemy session (provided by ``get_db``).
        name:
            Display name of the workspace.
        owner_username:
            Username of the workspace owner.
        description:
            Optional longer description.

        Returns
        -------
        Workspace
            The newly created workspace with its ``id`` populated.
        """
        workspace = Workspace(
            name=name,
            owner_username=owner_username,
            description=description,
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace

    @staticmethod
    def get_by_id(session: Session, workspace_id: int) -> Workspace | None:
        """Return a workspace by primary key, or ``None`` if not found.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        workspace_id:
            Primary key of the workspace.
        """
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def list_for_user(session: Session, username: str) -> list[Workspace]:
        """Return all workspaces owned by *username*, newest-updated first.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        username:
            Owner username to filter by.
        """
        stmt = (
            select(Workspace)
            .where(Workspace.owner_username == username)
            .order_by(Workspace.updated_at.desc())
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def list_all(session: Session) -> list[Workspace]:
        """Return every workspace (admin view), newest-updated first.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        """
        stmt = select(Workspace).order_by(Workspace.updated_at.desc())
        result = session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def resolve_from_model_string(
        session: Session, model_string: str
    ) -> Workspace | None:
        """Resolve a workspace from a model string that may be an ID or name.

        Open WebUI may send either the original model ID (``pageindex-ws-3``)
        or a user-renamed model name (``Page Index Space``).  This helper
        tries the canonical ID pattern first, then falls back to matching
        against workspace names.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        model_string:
            The ``model`` value from the chat request.

        Returns
        -------
        Workspace | None
            The resolved workspace, or ``None`` if no match is found.
        """
        import re

        # 1. Try canonical pattern: pageindex-ws-{id}
        match = re.search(r"pageindex-ws-(\d+)", model_string)
        if match:
            ws_id = int(match.group(1))
            stmt = select(Workspace).where(Workspace.id == ws_id)
            result = session.execute(stmt)
            ws = result.scalars().first()
            if ws is not None:
                return ws

        # 2. Fallback: check if it's a bare integer
        stripped = model_string.strip()
        if stripped.isdigit():
            stmt = select(Workspace).where(Workspace.id == int(stripped))
            result = session.execute(stmt)
            ws = result.scalars().first()
            if ws is not None:
                return ws

        # 3. Fallback: try to match the model string against the friendly
        #    name pattern "PageIndex: {workspace_name}"
        if model_string.lower().startswith("pageindex:"):
            ws_name = model_string.split(":", 1)[1].strip()
            stmt = select(Workspace).where(Workspace.name == ws_name)
            result = session.execute(stmt)
            ws = result.scalars().first()
            if ws is not None:
                return ws

        # 4. Fallback: direct workspace name match (for renamed models)
        stmt = select(Workspace).where(Workspace.name == model_string)
        result = session.execute(stmt)
        ws = result.scalars().first()
        if ws is not None:
            return ws

        # 5. Fallback: case-insensitive partial match
        stmt = select(Workspace).where(
            Workspace.name.ilike(f"%{model_string}%")
        )
        result = session.execute(stmt)
        ws = result.scalars().first()
        if ws is not None:
            return ws

        # 6. Last resort: if exactly one workspace exists, use it.
        #    This handles the case where the user renamed the model in
        #    Open WebUI to something completely different (e.g. "Page
        #    Index Space") that bears no resemblance to the workspace
        #    name.  When there's only one workspace, the intent is
        #    unambiguous.
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(Workspace)
        total = session.execute(count_stmt).scalar() or 0
        if total == 1:
            stmt = select(Workspace)
            result = session.execute(stmt)
            return result.scalars().first()

        return None

    @staticmethod
    def delete(session: Session, workspace_id: int) -> bool:
        """Delete a workspace and cascade-delete its documents.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        workspace_id:
            Primary key of the workspace to remove.

        Returns
        -------
        bool
            ``True`` if a workspace was found and deleted, ``False`` otherwise.
        """
        stmt = (
            delete(Workspace)
            .where(Workspace.id == workspace_id)
            .execution_options(synchronize_session="fetch")
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0

    @staticmethod
    def rename(session: Session, workspace_id: int, new_name: str) -> bool:
        """Rename an existing workspace.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        workspace_id:
            Primary key of the workspace to rename.
        new_name:
            The new display name.

        Returns
        -------
        bool
            ``True`` if the workspace was found and renamed, ``False``
            otherwise.
        """
        stmt = (
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(name=new_name)
            .execution_options(synchronize_session="fetch")
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0

    @staticmethod
    def update(
        session: Session,
        workspace_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> Workspace | None:
        """Update workspace name and/or description.

        Only non-``None`` fields are changed.  Returns the updated workspace
        or ``None`` if not found.
        """
        values: dict = {}
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description
        if not values:
            return WorkspaceRepo.get_by_id(session, workspace_id)

        stmt = (
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        session.execute(stmt)
        session.commit()
        return WorkspaceRepo.get_by_id(session, workspace_id)


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------
class DocumentRepo:
    """Data-access helpers for the :class:`Document` model."""

    @staticmethod
    def create(
        session: Session,
        workspace_id: int,
        username: str,
        file_name: str,
        file_hash: str,
        file_size: int,
        doc_title: str,
        root_summary: str,
        node_count: int,
        image_count: int,
        page_count: int,
    ) -> Document:
        """Insert a new document record and return it.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        workspace_id:
            Foreign key pointing to the parent workspace.
        username:
            Username of the person who uploaded the document.
        file_name:
            Original file name (e.g. ``"report.pdf"``).
        file_hash:
            SHA-256 (or similar) hex digest of the raw file.
        file_size:
            Size of the file in bytes.
        doc_title:
            Title extracted from the document content.
        root_summary:
            Summary generated for the root node of the document tree.
        node_count:
            Total number of tree nodes produced by the indexer.
        image_count:
            Number of images extracted from the document.
        page_count:
            Number of pages in the source document.

        Returns
        -------
        Document
            The newly created document with its ``id`` populated.
        """
        document = Document(
            workspace_id=workspace_id,
            username=username,
            file_name=file_name,
            file_hash=file_hash,
            file_size=file_size,
            doc_title=doc_title,
            root_summary=root_summary,
            node_count=node_count,
            image_count=image_count,
            page_count=page_count,
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document

    @staticmethod
    def list_for_workspace(
        session: Session, workspace_id: int
    ) -> list[Document]:
        """Return all documents in a workspace, newest first.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        workspace_id:
            Foreign key of the target workspace.
        """
        stmt = (
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def get_by_id(session: Session, doc_id: int) -> Document | None:
        """Return a document by primary key, or ``None`` if not found.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        doc_id:
            Primary key of the document.
        """
        stmt = select(Document).where(Document.id == doc_id)
        result = session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def get_by_hash_in_workspace(
        session: Session, workspace_id: int, file_hash: str
    ) -> Document | None:
        """Check whether a file already exists in the workspace.

        This is used for de-duplication: if the same file (by content hash)
        has already been uploaded to this workspace, the caller can skip
        re-processing.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        workspace_id:
            Foreign key of the target workspace.
        file_hash:
            Hash digest of the file to look up.

        Returns
        -------
        Document | None
            The existing document if found, otherwise ``None``.
        """
        stmt = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.file_hash == file_hash,
        )
        result = session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def update_metadata(
        session: Session,
        doc_id: int,
        file_name: str | None = None,
        doc_title: str | None = None,
    ) -> Document | None:
        """Update document display name and/or title.

        Only non-``None`` fields are changed.  Returns the updated document
        or ``None`` if not found.
        """
        values: dict = {}
        if file_name is not None:
            values["file_name"] = file_name
        if doc_title is not None:
            values["doc_title"] = doc_title
        if not values:
            return DocumentRepo.get_by_id(session, doc_id)

        stmt = (
            update(Document)
            .where(Document.id == doc_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        session.execute(stmt)
        session.commit()
        return DocumentRepo.get_by_id(session, doc_id)

    @staticmethod
    def update_from_reindex(
        session: Session,
        doc_id: int,
        file_name: str,
        file_hash: str,
        file_size: int,
        doc_title: str,
        root_summary: str,
        node_count: int,
        image_count: int,
        page_count: int,
    ) -> Document | None:
        """Replace all content-related fields after a document re-upload.

        This keeps the same ``doc_id`` so that chat history references
        remain valid.
        """
        stmt = (
            update(Document)
            .where(Document.id == doc_id)
            .values(
                file_name=file_name,
                file_hash=file_hash,
                file_size=file_size,
                doc_title=doc_title,
                root_summary=root_summary,
                node_count=node_count,
                image_count=image_count,
                page_count=page_count,
            )
            .execution_options(synchronize_session="fetch")
        )
        session.execute(stmt)
        session.commit()
        return DocumentRepo.get_by_id(session, doc_id)

    @staticmethod
    def delete(session: Session, doc_id: int) -> bool:
        """Delete a single document record.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        doc_id:
            Primary key of the document to remove.

        Returns
        -------
        bool
            ``True`` if a document was found and deleted, ``False`` otherwise.
        """
        stmt = (
            delete(Document)
            .where(Document.id == doc_id)
            .execution_options(synchronize_session="fetch")
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0
