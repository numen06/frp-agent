"""Optional isolated Web SSH worker for deployments whose gateways cannot restart."""
from fastapi import FastAPI
from app.routers.webssh import router
from app.routers.managed_host import list_hosts, update_host, test_host, delete_host, get_rdp_fingerprint
from app.routers.host_discovery import router as discovery_router

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(router)
from app.routers.webvnc import router as webvnc_router
app.include_router(webvnc_router)
app.include_router(discovery_router)
app.post('/api/managed-hosts/rdp/fingerprint')(get_rdp_fingerprint)
app.get('/api/managed-hosts')(list_hosts)
app.put('/api/managed-hosts/{host_id}')(update_host)
app.delete('/api/managed-hosts/{host_id}', status_code=204)(delete_host)
app.post('/api/managed-hosts/{host_id}/test')(test_host)


@app.get("/health")
def health():
    return {"status": "ok"}
