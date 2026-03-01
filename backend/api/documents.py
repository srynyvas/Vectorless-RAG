"""Document and workspace management endpoints.

Provides full CRUD for workspaces and documents, including file upload
with automatic parsing and tree-index construction.  All endpoints live
under the ``/api`` prefix.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.repos import WorkspaceRepo, DocumentRepo
from backend.api.models import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    DocumentUpdate,
    DocumentResponse,
)
from backend.core.document_manager import (
    compute_file_hash,
    cache_path,
    load_cached_tree,
    save_cached_tree,
    delete_cached_tree,
    parse_and_index,
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


# ===================================================================
# Helper: convert ORM objects to response models
# ===================================================================

def _workspace_to_response(ws, doc_count: int = 0) -> WorkspaceResponse:
    """Convert a Workspace ORM instance to a WorkspaceResponse."""
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description or "",
        owner_username=ws.owner_username,
        doc_count=doc_count,
        created_at=ws.created_at.isoformat() if ws.created_at else "",
    )


def _document_to_response(doc) -> DocumentResponse:
    """Convert a Document ORM instance to a DocumentResponse."""
    return DocumentResponse(
        id=doc.id,
        workspace_id=doc.workspace_id,
        file_name=doc.file_name,
        doc_title=doc.doc_title or "",
        root_summary=doc.root_summary or "",
        node_count=doc.node_count or 0,
        image_count=doc.image_count or 0,
        page_count=doc.page_count or 0,
        file_size=doc.file_size or 0,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
    )


# ===================================================================
# Workspace CRUD
# ===================================================================

@router.post("/workspaces", response_model=WorkspaceResponse)
def create_workspace(
    body: WorkspaceCreate,
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    """Create a new workspace.

    Parameters
    ----------
    body:
        JSON body with ``name``, ``description``, and ``owner_username``.
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    WorkspaceResponse
        The newly created workspace.
    """
    ws = WorkspaceRepo.create(
        session=db,
        name=body.name,
        owner_username=body.owner_username,
        description=body.description,
    )
    return _workspace_to_response(ws, doc_count=0)


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(
    owner_username: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    """List workspaces, optionally filtered by owner.

    Parameters
    ----------
    owner_username:
        If provided, return only workspaces owned by this user.
        If omitted, return all workspaces.
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    list[WorkspaceResponse]
        Workspaces with their ``doc_count`` populated.
    """
    if owner_username:
        workspaces = WorkspaceRepo.list_for_user(db, owner_username)
    else:
        workspaces = WorkspaceRepo.list_all(db)

    results: list[WorkspaceResponse] = []
    for ws in workspaces:
        docs = DocumentRepo.list_for_workspace(db, ws.id)
        results.append(_workspace_to_response(ws, doc_count=len(docs)))
    return results


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a workspace and all associated documents and cache files.

    Parameters
    ----------
    workspace_id:
        Primary key of the workspace to delete.
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    dict
        ``{"deleted": true}`` on success.

    Raises
    ------
    HTTPException 404
        If the workspace does not exist.
    """
    ws = WorkspaceRepo.get_by_id(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Delete cached tree files for every document in the workspace
    docs = DocumentRepo.list_for_workspace(db, workspace_id)
    for doc in docs:
        try:
            delete_cached_tree(doc.username, doc.file_hash)
        except Exception as exc:
            logger.warning(
                "Failed to delete cache for doc %s (hash=%s): %s",
                doc.id, doc.file_hash, exc,
            )

    # Delete workspace (cascades to documents in DB)
    WorkspaceRepo.delete(db, workspace_id)
    return {"deleted": True}


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    body: WorkspaceUpdate,
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    """Update workspace name and/or description.

    Only non-null fields in the request body are updated.
    """
    ws = WorkspaceRepo.get_by_id(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    updated = WorkspaceRepo.update(
        db, workspace_id, name=body.name, description=body.description,
    )
    docs = DocumentRepo.list_for_workspace(db, workspace_id)
    return _workspace_to_response(updated, doc_count=len(docs))


# ===================================================================
# Document CRUD
# ===================================================================

@router.post("/documents/upload", response_model=DocumentResponse)
def upload_document(
    workspace_id: int = Form(...),
    username: str = Form(...),
    quick_index: bool = Form(default=False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Upload a document, parse it, build the tree index, and store metadata.

    The upload flow:
    1. Validate that the target workspace exists.
    2. Compute an MD5 hash of the file content.
    3. If a document with the same hash already exists in the workspace,
       return the existing record (de-duplication).
    4. Save the uploaded content to a temporary file.
    5. Parse and build the tree index via ``parse_and_index``.
    6. Persist the tree to the JSON cache.
    7. Create a ``Document`` row in the database.
    8. Clean up the temporary file.

    Parameters
    ----------
    workspace_id:
        ID of the workspace to add the document to.
    username:
        Username of the uploader.
    quick_index:
        If ``True``, skip LLM summaries and use text snippets instead.
    file:
        The uploaded file.
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    DocumentResponse
        Metadata for the newly processed (or existing) document.

    Raises
    ------
    HTTPException 404
        If the workspace does not exist.
    HTTPException 500
        If parsing or indexing fails.
    """
    # 1. Validate workspace
    ws = WorkspaceRepo.get_by_id(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # 2. Read content and compute hash
    content = file.file.read()
    file_hash = compute_file_hash(content)
    file_size = len(content)

    # 3. De-duplication check
    existing = DocumentRepo.get_by_hash_in_workspace(db, workspace_id, file_hash)
    if existing:
        return _document_to_response(existing)

    # 4. Save to temp file
    ext = os.path.splitext(file.filename or "upload")[1].lower()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"{file_hash}{ext}"

    try:
        tmp_path.write_bytes(content)

        # 5. Parse and index
        tree, metadata = parse_and_index(
            file_path=str(tmp_path),
            file_name=file.filename or "upload",
            username=username,
            quick_index=quick_index,
        )

        # 6. Save cached tree
        save_cached_tree(username, file_hash, tree)

        # 7. Create document record in DB
        doc = DocumentRepo.create(
            session=db,
            workspace_id=workspace_id,
            username=username,
            file_name=file.filename or "upload",
            file_hash=file_hash,
            file_size=file_size,
            doc_title=metadata["doc_title"],
            root_summary=metadata["root_summary"],
            node_count=metadata["node_count"],
            image_count=metadata["image_count"],
            page_count=metadata["page_count"],
        )

        return _document_to_response(doc)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to process document upload: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {exc}",
        )
    finally:
        # 8. Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    workspace_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    """List all documents in a workspace.

    Parameters
    ----------
    workspace_id:
        The workspace whose documents to list (required).
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    list[DocumentResponse]
        Documents in the workspace, newest first.
    """
    docs = DocumentRepo.list_for_workspace(db, workspace_id)
    return [_document_to_response(doc) for doc in docs]


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Get metadata for a single document.

    Parameters
    ----------
    doc_id:
        Primary key of the document.
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    DocumentResponse
        Full document metadata.

    Raises
    ------
    HTTPException 404
        If the document does not exist.
    """
    doc = DocumentRepo.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_to_response(doc)


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a document and its associated cache file.

    Parameters
    ----------
    doc_id:
        Primary key of the document to delete.
    db:
        SQLAlchemy session (injected).

    Returns
    -------
    dict
        ``{"deleted": true}`` on success.

    Raises
    ------
    HTTPException 404
        If the document does not exist.
    """
    doc = DocumentRepo.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete cached tree file
    try:
        delete_cached_tree(doc.username, doc.file_hash)
    except Exception as exc:
        logger.warning(
            "Failed to delete cache for doc %s (hash=%s): %s",
            doc.id, doc.file_hash, exc,
        )

    # Delete DB record
    DocumentRepo.delete(db, doc_id)
    return {"deleted": True}


@router.patch("/documents/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: int,
    body: DocumentUpdate,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Update document metadata (title, display name).

    Only non-null fields in the request body are updated.
    """
    doc = DocumentRepo.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    updated = DocumentRepo.update_metadata(
        db, doc_id, file_name=body.file_name, doc_title=body.doc_title,
    )
    return _document_to_response(updated)


@router.post("/documents/{doc_id}/replace", response_model=DocumentResponse)
def replace_document(
    doc_id: int,
    username: str = Form(...),
    quick_index: bool = Form(default=False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Replace a document with a new version.

    Keeps the same ``doc_id`` so chat history references remain valid.
    Deletes the old cached tree, re-parses and re-indexes the new file,
    and updates all content-related fields in the database.
    """
    doc = DocumentRepo.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete old cached tree
    try:
        delete_cached_tree(doc.username, doc.file_hash)
    except Exception as exc:
        logger.warning("Failed to delete old cache for doc %s: %s", doc_id, exc)

    # Read new file content
    content = file.file.read()
    file_hash = compute_file_hash(content)
    file_size = len(content)

    # Save to temp file
    ext = os.path.splitext(file.filename or "upload")[1].lower()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"{file_hash}{ext}"

    try:
        tmp_path.write_bytes(content)

        # Parse and index
        tree, metadata = parse_and_index(
            file_path=str(tmp_path),
            file_name=file.filename or "upload",
            username=username,
            quick_index=quick_index,
        )

        # Save new cached tree
        save_cached_tree(username, file_hash, tree)

        # Update DB record (same doc_id)
        updated = DocumentRepo.update_from_reindex(
            session=db,
            doc_id=doc_id,
            file_name=file.filename or "upload",
            file_hash=file_hash,
            file_size=file_size,
            doc_title=metadata["doc_title"],
            root_summary=metadata["root_summary"],
            node_count=metadata["node_count"],
            image_count=metadata["image_count"],
            page_count=metadata["page_count"],
        )

        return _document_to_response(updated)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to replace document: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to replace document: {exc}",
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ===================================================================
# Tree endpoints (for React UI tree viewer)
# ===================================================================

@router.get("/documents/{doc_id}/tree")
def get_document_tree(
    doc_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Return the lightweight tree structure for a document.

    Returns the tree in ``to_search_dict()`` format -- node IDs, titles,
    summaries, and page ranges but **no full text**.  This keeps the
    payload small for the frontend tree viewer.
    """
    doc = DocumentRepo.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    tree = load_cached_tree(doc.username, doc.file_hash)
    if tree is None:
        raise HTTPException(
            status_code=404,
            detail="Document tree index not found. The document may need to be re-uploaded.",
        )

    return tree.to_search_dict()


@router.get("/documents/{doc_id}/tree/{node_id:path}")
def get_tree_node_detail(
    doc_id: int,
    node_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Return full text and images for a specific tree node.

    Used by the frontend to lazy-load node details when a user clicks
    on a node in the tree viewer.
    """
    doc = DocumentRepo.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    tree = load_cached_tree(doc.username, doc.file_hash)
    if tree is None:
        raise HTTPException(status_code=404, detail="Tree index not found")

    # Handle root node
    if node_id == "root":
        return {
            "node_id": tree.node_id,
            "title": tree.title,
            "summary": tree.summary,
            "text": tree.text,
            "images": tree.images,
            "start_page": tree.start_page,
            "end_page": tree.end_page,
        }

    # Find node by ID
    matches = tree.find_nodes_by_ids([node_id])
    if not matches:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in tree")

    node = matches[0]
    return {
        "node_id": node.node_id,
        "title": node.title,
        "summary": node.summary,
        "text": node.text,
        "images": node.images,
        "start_page": node.start_page,
        "end_page": node.end_page,
    }
