from fastapi import APIRouter, HTTPException
from pydantic import UUID4

from app.models import NodeModel
from app.schemas.nodes import Node, NodeStatus
from app.schemas.requests import CreateNodeRequest, UpdateNodeRequest
from app.schemas.responses import NodeListResponse, NodeResponse

router = APIRouter(prefix="/api/nodes")


@router.post("/", response_model=NodeResponse)
def create_node(request: CreateNodeRequest):
    node = Node(
        status=NodeStatus.ACTIVE,
        node_resources=request.node_resources,
    )
    NodeModel.synchronize_schema(node)
    return NodeResponse(status="OK", data=node)


@router.get("/{node_id}/", response_model=NodeResponse)
def retrieve_node(node_id: UUID4):
    try:
        node = NodeModel.retrieve_schema(str(node_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return NodeResponse(status="OK", data=node)


@router.patch("/{node_id}/", response_model=NodeResponse)
def update_node(node_id: UUID4, request: UpdateNodeRequest):
    try:
        node = NodeModel.retrieve_schema(str(node_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    node.status = NodeStatus.ACTIVE
    node.node_resources = request.node_resources

    NodeModel.synchronize_schema(node)
    return NodeResponse(status="OK", data=node)


@router.delete("/{node_id}/", response_model=NodeResponse)
def delete_node(node_id: UUID4):
    try:
        node = NodeModel.retrieve_schema(str(node_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    node.status = NodeStatus.DELETED
    node.node_resources = None
    node.available_resources = None

    NodeModel.synchronize_schema(node)
    return NodeResponse(status="OK", data=node)


@router.get("/", response_model=NodeListResponse)
def list_nodes():
    return NodeListResponse(status="OK", data=NodeModel.retrieve_schemas())
