from fastapi import APIRouter
from pydantic import UUID4

from app.schemas.requests import CreateNodeRequest, DeleteNodeRequest, UpdateNodeRequest
from app.schemas.responses import NodeListResponse, NodeResponse

router = APIRouter(prefix='/api/nodes')


@router.post('/', response_model=NodeResponse)
def create_node(request: CreateNodeRequest):
    pass


@router.get('/{node_id}/', response_model=NodeResponse)
def retrieve_node(node_id: UUID4):
    pass


@router.patch('/', response_model=NodeResponse)
def update_node(request: UpdateNodeRequest):
    pass


@router.delete('/', response_model=NodeResponse)
def delete_node(request: DeleteNodeRequest):
    pass


@router.get('/', response_model=NodeListResponse)
def list_nodes():
    pass
