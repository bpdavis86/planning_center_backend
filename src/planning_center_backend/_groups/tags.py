from typing import Optional, Sequence, Union
from urllib.parse import urljoin

from .._json_schemas.groups import TagsSchema, TagSchema, TagData
from ..api_provider import ApiProvider
from .. import _urls as urls

__all__ = ['TagsApiProvider']


class TagsApiProvider(ApiProvider):
    """
    Provide v2 API access to the registered tags system.
    """
    def query(self, name: Optional[str] = None) -> Sequence[TagData]:
        """
        Query for a list of tags matching the given name.
        :param name: Name pattern to query
        :return: Resulting tag description objects
        """
        params = {}
        if name is not None:
            params['where[name]'] = name
        return self.query_api(urls.GROUPS_TAGS_URL, params=params, schema=TagsSchema)

    def get(self, id_: Union[int, str]) -> TagData:
        """
        Retrieve a tag by its unique numeric identifier
        :param id_: Tag numeric id, as int or str
        :return: Associated tag object
        """
        url = urljoin(urls.GROUPS_TAGS_URL + '/', f'{id_}')
        return self.query_api(url=url, schema=TagSchema)
