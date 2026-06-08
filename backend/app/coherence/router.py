from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.coherence import pipeline
from app.coherence.schemas import ValidationOut
from app.coherence.service import get_gateway
from app.constructor.node_types import NodeType
from app.db import get_session

router = APIRouter(prefix="/api/projects", tags=["coherence"])


@router.post("/{project_id}/nodes/{node_type}/validate", response_model=ValidationOut)
async def validate(
    project_id: str,
    node_type: NodeType,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    gateway=Depends(get_gateway),
):
    try:
        out = await pipeline.validate_node(
            session,
            gateway=gateway,
            user_id=user.id,
            tier=user.tier,
            project_id=project_id,
            node_type=node_type,
            today=datetime.now(timezone.utc).date(),
        )
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

    return ValidationOut(
        status=out.status.value,
        score=out.verdict.score if out.verdict else None,
        issues=out.verdict.issues if out.verdict else [],
        suggestions=out.verdict.suggestions if out.verdict else [],
        summary=out.verdict.summary if out.verdict else None,
        mode=out.gate.mode if out.gate else None,
        blocked=out.gate.blocked if out.gate else False,
        message=out.message,
        node_state=out.node_state,
    )
