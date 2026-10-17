"""Bounded SQL pagination shared by collection endpoints."""
from typing import Generic, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import or_

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams:
    def __init__(
        self,
        page: Optional[int] = Query(None, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        search: Optional[str] = Query(None, max_length=200),
    ):
        self.page = page
        self.page_size = page_size
        self.search = (search or "").strip()


def search_query(query, search, *columns):
    if search:
        query = query.filter(or_(*(column.icontains(search, autoescape=True) for column in columns)))
    return query


def paginate(query, params, transform=lambda row: row):
    """Legacy array responses stay bounded; explicit page requests include totals."""
    total = query.order_by(None).count() if params.page is not None else None
    rows = query.offset(((params.page or 1) - 1) * params.page_size).limit(params.page_size).all()
    items = [transform(row) for row in rows]
    if params.page is None:
        return items
    return dict(items=items, total=total, page=params.page, page_size=params.page_size)
