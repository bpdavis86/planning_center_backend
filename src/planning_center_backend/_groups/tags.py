from typing import Optional, Sequence, Union
from urllib.parse import urljoin

from .._json_schemas.groups import TagsSchema, TagSchema, TagData
from ..api_provider import ApiProvider
from .. import _urls as urls

__all__ = ['TagsApiProvider']


class TagsApiProvider(ApiProvider):
    def query(self, name: Optional[str] = None) -> Sequence[TagData]:
        params = {}
        if name is not None:
            params['where[name]'] = name
        return self.query_api(urls.GROUPS_TAGS_URL, params=params, schema=TagsSchema)

    def get(self, id_: Union[int, str]) -> TagData:
        url = urljoin(urls.GROUPS_TAGS_URL + '/', f'{id_}')
        return self.query_api(url=url, schema=TagSchema)
