from __future__ import annotations

from typing import Optional, Any

import msgspec

# region Base Objects


class ApiBase(msgspec.Struct):
    """
    Base object for all API query returns.
    """
    data: Any
    included: list
    meta: dict
    links: Optional[dict] = None


class _DataBase(msgspec.Struct, forbid_unknown_fields=True):
    """
    Base class for API 'data' field contents (generic attributes dict).
    """
    type: str
    id: str
    attributes: dict
    links: Optional[dict] = None
    relationships: Optional[dict] = None


# endregion
