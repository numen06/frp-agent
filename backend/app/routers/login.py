"""Interactive login: single-use CAPTCHA followed by shared password backoff."""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import authenticate_http_user
from app.database import get_db
from app.services.login_guard import client_address, login_guard

router = APIRouter(prefix='/api/auth', tags=['登录'])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    challenge_id: str = Field(min_length=1, max_length=128)
    captcha: str = Field(min_length=1, max_length=16)


@router.get('/captcha')
def captcha(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return login_guard.challenge(client_address(request))


@router.post('/login')
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    # authenticate_http_user holds the same attempt lock used by Basic Auth.
    user = authenticate_http_user(db, payload.username, payload.password, request,
                                 challenge=(payload.challenge_id, payload.captcha))
    return dict(success=True, username=user.username, role=user.role)
