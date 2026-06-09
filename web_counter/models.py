"""Pydantic request/response models."""

from typing import Dict, Optional
from pydantic import BaseModel


class VisitRequest(BaseModel):
    path: str = "/"
    title: Optional[str] = None


class CountResponse(BaseModel):
    today_pv: int = 0
    today_uv: int = 0
    site_pv: int = 0
    site_uv: int = 0
    pages: Dict[str, int] = {}


class ResetRequest(BaseModel):
    scope: str  # "today", "all", "page"
    path: Optional[str] = None


class OffsetRequest(BaseModel):
    site_pv: Optional[int] = None
    site_uv: Optional[int] = None
    pages: Optional[Dict[str, int]] = None


class LoginRequest(BaseModel):
    username: str
    password: str
