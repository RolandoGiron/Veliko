from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constructor.freshness import compute_state
from app.constructor.hashing import compute_node_hash
from app.constructor.models import Node, ResearchProject
from app.constructor.node_types import DEPENDENCY_CHAIN, NodeType


class ProjectNotFound(Exception):
    pass


async def create_project(
    session: AsyncSession, user_id: str, title: str, language: str
) -> ResearchProject:
    project = ResearchProject(user_id=user_id, title=title, language=language)
    session.add(project)
    await session.flush()
    for nt in DEPENDENCY_CHAIN:
        session.add(Node(project_id=project.id, type=nt.value, content=""))
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects(session: AsyncSession, user_id: str) -> list[ResearchProject]:
    res = await session.scalars(
        select(ResearchProject).where(ResearchProject.user_id == user_id)
    )
    return list(res)


async def _get_owned_project(
    session: AsyncSession, user_id: str, project_id: str
) -> ResearchProject:
    project = await session.get(ResearchProject, project_id)
    if project is None or project.user_id != user_id:
        raise ProjectNotFound(project_id)
    return project


async def _nodes_by_type(session: AsyncSession, project_id: str) -> dict[NodeType, Node]:
    res = await session.scalars(select(Node).where(Node.project_id == project_id))
    return {NodeType(n.type): n for n in res}


async def get_graph(
    session: AsyncSession, user_id: str, project_id: str
) -> tuple[ResearchProject, list[tuple[Node, str]]]:
    project = await _get_owned_project(session, user_id, project_id)
    nodes = await _nodes_by_type(session, project_id)
    contents = {nt: n.content for nt, n in nodes.items()}
    ordered: list[tuple[Node, str]] = []
    for nt in DEPENDENCY_CHAIN:
        node = nodes[nt]
        state = compute_state(
            compute_node_hash(nt, contents), node.last_validated_hash
        )
        ordered.append((node, state.value))
    return project, ordered


async def upsert_node_content(
    session: AsyncSession, user_id: str, project_id: str, node_type: NodeType, content: str
) -> Node:
    await _get_owned_project(session, user_id, project_id)
    node = await session.scalar(
        select(Node).where(Node.project_id == project_id, Node.type == node_type.value)
    )
    if node is None:
        raise ProjectNotFound(project_id)
    node.content = content
    await session.commit()
    await session.refresh(node)
    return node
