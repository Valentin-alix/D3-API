from typing import Type, TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql.base import ExecutableOption

from src.models.base import Base


def get_auto_id(session: Session, model: Type[Base]) -> int:
    return session.query(func.max(model.id)).scalar() + 1  # type: ignore


T = TypeVar("T")


def get_or_create(
    session: Session,
    model: Type[T],
    commit: bool = True,
    options: list[ExecutableOption] | None = None,
    defaults: dict | None = None,
    **kwargs,
) -> tuple[T, bool]:
    query = session.query(model).filter_by(**kwargs)
    if options is not None:
        query = query.options(*options)

    instance = query.first()
    if instance is not None:
        return instance, False
    else:
        kwargs |= defaults or {}
        instance = model(**kwargs)
        session.add(instance)
        if commit:
            session.commit()
        return instance, True
