from fastapi import APIRouter
from pydantic import UUID4

from app.schemas.requests import CreateServiceRequest, UpdateServiceRequest, DeleteServiceRequest
from app.schemas.responses import ServiceResponse, ServiceListResponse

router = APIRouter(prefix='/api/services')


@router.post('/', response_model=ServiceResponse)
def create_service(request: CreateServiceRequest):
    pass


@router.get('/{service_id}/')
def retrieve_service(service_id: UUID4):
    pass


@router.patch('/', response_model=ServiceResponse)
def update_service(request: UpdateServiceRequest):
    pass


@router.delete('/', response_model=ServiceResponse)
def delete_service(request: DeleteServiceRequest):
    pass


@router.get('/', response_model=ServiceListResponse)
def list_services():
    pass
