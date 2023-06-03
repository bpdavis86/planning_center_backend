from __future__ import annotations

from datetime import date, datetime
from typing import Optional, NamedTuple, Sequence, Union
from urllib.parse import urljoin

from . import _urls as urls
from ._json_schemas.people import PeopleSchema, PersonSchema, PersonData
from .api_provider import ApiProvider


class PeopleQueryExpression(NamedTuple):
    accounting_administrator: Optional[bool] = None
    anniversary: Optional[date] = None
    birthdate: Optional[date] = None
    child: Optional[bool] = None
    created_at: Optional[datetime] = None
    first_name: Optional[str] = None
    gender: Optional[str] = None
    given_name: Optional[str] = None
    grade: Optional[int] = None
    graduation_year: Optional[int] = None
    id_: Optional[int] = None
    inactivated_at: Optional[datetime] = None
    last_name: Optional[str] = None
    medical_notes: Optional[str] = None
    membership: Optional[str] = None
    middle_name: Optional[str] = None
    nickname: Optional[str] = None
    people_permissions: Optional[str] = None
    remote_id: Optional[int] = None
    search_name: Optional[str] = None
    search_name_or_email: Optional[str] = None
    search_name_or_email_or_phone_number: Optional[str] = None
    search_phone_number: Optional[str] = None
    search_phone_number_e164: Optional[str] = None
    site_administrator: Optional[bool] = None
    status: Optional[str] = None
    updated_at: Optional[datetime] = None


class PeopleApiProvider(ApiProvider):
    def query(
            self,
            expr: Union[str, PeopleQueryExpression],
            per_page: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Sequence[PersonData]:
        if isinstance(expr, str):
            expr = PeopleQueryExpression(search_name=expr)
        _expr_d = expr._asdict()
        _expr_d_c = _expr_d.copy()
        for k, v in _expr_d_c.items():
            if v is None:
                continue
            elif isinstance(v, int):
                _expr_d[k] = str(v)
            elif isinstance(v, (date, datetime)):
                _expr_d[k] = v.isoformat()
            elif not isinstance(v, str):
                raise ValueError(f'Incorrect type {type(v)} for query field {k}')
        query_params = {f'where[{k}]': v for k, v in _expr_d.items() if v is not None}
        if per_page is not None:
            query_params['per_page'] = str(per_page)
        if offset is not None:
            query_params['offset'] = str(offset)

        return self.query_api(url=urls.PEOPLE_API_BASE_URL, params=query_params, schema=PeopleSchema)

    def get(self, id_: int) -> PersonData:
        url = urljoin(urls.PEOPLE_API_BASE_URL + '/', f'{id_}')
        return self.query_api(url=url, schema=PersonSchema)
