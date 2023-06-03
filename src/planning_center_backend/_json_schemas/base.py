from __future__ import annotations

from typing import Optional

import msgspec

# region Base Objects


class ApiBase(msgspec.Struct):
    data: dict
    included: list
    meta: dict
    links: Optional[dict] = None


class _DataBase(msgspec.Struct, forbid_unknown_fields=True):
    type: str
    id: str
    attributes: dict
    links: Optional[dict] = None
    relationships: Optional[dict] = None


# endregion
