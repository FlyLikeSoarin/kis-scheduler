from fastapi import FastAPI

from app.api import events_router, monitoring_router, nodes_router, services_router

app = FastAPI()

app.include_router(events_router)
app.include_router(monitoring_router)
app.include_router(nodes_router)
app.include_router(services_router)
