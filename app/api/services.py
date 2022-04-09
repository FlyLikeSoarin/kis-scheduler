from fastapi import APIRouter, HTTPException
from pydantic import UUID4

from app.models.services import ServiceModel
from app.schemas.requests import CreateServiceRequest, UpdateServiceRequest
from app.schemas.responses import ServiceListResponse, ServiceResponse
from app.schemas.services import Service, ServiceStatus

router = APIRouter(prefix="/api/services")


@router.post("/", response_model=ServiceResponse)
def create_service(request: CreateServiceRequest):
    service = Service(
        status=ServiceStatus.ACTIVE,
        type=request.type,
        resource_limit=request.resource_limit,
    )
    ServiceModel.synchronize_schema(service)
    return ServiceResponse(status="OK", data=service)


@router.get("/{service_id}/")
def retrieve_service(service_id: UUID4):
    try:
        node = ServiceModel.retrieve_schema(str(service_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ServiceResponse(status="OK", data=node)


@router.patch("/{service_id}/", response_model=ServiceResponse)
def update_service(service_id: UUID4, request: UpdateServiceRequest):
    try:
        service = ServiceModel.retrieve_schema(str(service_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    service.status = ServiceStatus.ACTIVE
    service.resource_limit = request.resource_limit

    ServiceModel.synchronize_schema(service)
    return ServiceResponse(status="OK", data=service)


@router.delete("/{service_id}/", response_model=ServiceResponse)
def delete_service(service_id: UUID4):
    try:
        service = ServiceModel.retrieve_schema(str(service_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    service.status = ServiceStatus.DELETED
    service.resource_limit = None

    ServiceModel.synchronize_schema(service)
    return ServiceResponse(status="OK", data=service)


@router.get("/", response_model=ServiceListResponse)
def list_services():
    return ServiceListResponse(status="OK", data=ServiceModel.retrieve_schemas())
