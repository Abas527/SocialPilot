"""Shared authentication and project-ownership dependencies."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core import storage

bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = storage.get_active_auth_session(credentials.credentials)
    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


def require_project_owner(pid: str, user: dict = Depends(require_auth)) -> dict:
    owner = storage.get_project_owner(pid)
    if owner is None or owner["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Project not found.")
    return user
