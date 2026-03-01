"""GET /v1/models — expose workspaces as selectable models.

Open WebUI (and other OpenAI-compatible clients) call this endpoint to
populate the model dropdown.  Each workspace is surfaced as a "model"
whose ID follows the pattern ``pageindex-ws-{workspace_id}``.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.repos import WorkspaceRepo
from backend.api.models import ModelInfo, ModelListResponse

router = APIRouter()


@router.get("/v1/models")
def list_models(db: Session = Depends(get_db)):
    """Return all workspaces as selectable 'models' for Open WebUI.

    Each workspace appears as:
    - id: ``pageindex-ws-{workspace_id}``
    - owned_by: ``pageindex-rag``

    Open WebUI will show these in the model dropdown.
    """
    workspaces = WorkspaceRepo.list_all(db)
    models = []
    for ws in workspaces:
        models.append(
            ModelInfo(
                id=f"pageindex-ws-{ws.id}",
                name=f"PageIndex: {ws.name}",
                owned_by="pageindex-rag",
            )
        )
    return ModelListResponse(data=models)
