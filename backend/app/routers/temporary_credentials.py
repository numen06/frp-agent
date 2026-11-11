"""Monitor and manage temporary credentials issued by the native gateways."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.auth import get_current_user
from app.database import get_db
from app.services.host_access_service import add_audit_log, is_admin
from app.services.login_guard import client_address
from app.services.rdp_gateway_service import rdp_gateway_service
from app.services.vnc_gateway_service import vnc_gateway_service

router = APIRouter(prefix="/api/temporary-credentials", tags=["临时凭据"])
GATEWAYS = {"rdp": rdp_gateway_service, "vnc": vnc_gateway_service}
Protocol = Literal["rdp", "vnc"]


def platform_user(request: Request, user=Depends(get_current_user)):
    if user.id <= 0 or request.url.scheme != "https":
        raise HTTPException(403, "请通过 HTTPS 使用平台账号管理临时凭据")
    return user


def revalidate(gateway, row, db):
    if row.status == "active":
        try:
            return gateway.validate_temporary_credential(db, row.ticket)
        except HTTPException:
            row.revoke()
    return None


@router.get("")
def list_credentials(
    response: Response,
    protocol: Protocol | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(platform_user),
    db=Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    items = []
    for name, gateway in GATEWAYS.items():
        if protocol and name != protocol:
            continue
        store = gateway.temporary_credentials
        with store.lock:
            items.extend(store.metadata(row, user.id) for row in store.rows.values()
                         if row.ticket.user_id == user.id or is_admin(user))
    items.sort(key=lambda item: item["issued_at"], reverse=True)
    first = (page - 1) * page_size
    selected = items[first:first + page_size]
    for index, item in enumerate(selected):
        gateway = GATEWAYS[item["protocol"]]
        store = gateway.temporary_credentials
        with store.lock:
            row = store.rows.get(item["username"])
            if row:
                revalidate(gateway, row, db)
                selected[index] = store.metadata(row, user.id)
            else:
                item.update(status="expired", can_copy=False)
    return {"items": selected, "total": len(items), "page": page, "page_size": page_size}


@router.post("/{protocol}/{username}/copy")
def copy_credential(
    protocol: Protocol, username: str, response: Response,
    user=Depends(platform_user), db=Depends(get_db),
):
    gateway = GATEWAYS[protocol]
    store = gateway.temporary_credentials
    with store.lock:
        row = store.rows.get(username)
        if not row or row.ticket.user_id != user.id:
            raise HTTPException(404, "临时凭据不存在")
        if revalidate(gateway, row, db) is None:
            raise HTTPException(410, "临时凭据已失效")
        password = store.reveal(row)
        data = store.metadata(row, user.id)
    response.headers["Cache-Control"] = "no-store"
    return {**data, "password": password}


@router.delete("/{protocol}/{username}", status_code=204)
def revoke_credential(
    protocol: Protocol, username: str, request: Request,
    user=Depends(platform_user), db=Depends(get_db),
):
    gateway = GATEWAYS[protocol]
    store = gateway.temporary_credentials
    with store.lock:
        row = store.rows.get(username)
        if not row or (row.ticket.user_id != user.id and not is_admin(user)):
            raise HTTPException(404, "临时凭据不存在")
        access = revalidate(gateway, row, db)
        if access:
            _, host = access
            row.revoke()
            add_audit_log(db, host, user, "temporary_credential_revoked", "success",
                          client_address(request), target=host.name)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
