from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.constructor import service
from app.constructor.node_types import NodeType
from app.constructor.schemas import (
    NodeIn,
    NodeOut,
    ProjectDetail,
    ProjectIn,
    ProjectSummary,
)
from app.db import get_session

router = APIRouter(prefix="/api/projects", tags=["constructor"])


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    p = await service.create_project(session, user.id, body.title, body.language)
    return ProjectSummary(id=p.id, title=p.title, language=p.language)


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return [
        ProjectSummary(id=p.id, title=p.title, language=p.language)
        for p in await service.list_projects(session, user.id)
    ]


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        project, nodes = await service.get_graph(session, user.id, project_id)
    except service.ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return ProjectDetail(
        id=project.id,
        title=project.title,
        language=project.language,
        nodes=[NodeOut(type=n.type, content=n.content, state=state) for n, state in nodes],
    )


@router.put("/{project_id}/nodes/{node_type}", response_model=NodeOut)
async def update_node(
    project_id: str,
    node_type: NodeType,
    body: NodeIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        node = await service.upsert_node_content(
            session, user.id, project_id, node_type, body.content
        )
    except service.ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    # recompute single-node state for the response
    _, nodes = await service.get_graph(session, user.id, project_id)
    state = next(s for n, s in nodes if n.type == node_type.value)
    return NodeOut(type=node.type, content=node.content, state=state)
