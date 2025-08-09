import re

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    @declared_attr  # type: ignore
    def __tablename__(cls):
        # to snake_case
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
