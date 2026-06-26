from __future__ import annotations

from typing import Annotated
from uuid import UUID

from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column

UUIDPk = Annotated[UUID, mapped_column(PGUUID(as_uuid=True), primary_key=True)]
