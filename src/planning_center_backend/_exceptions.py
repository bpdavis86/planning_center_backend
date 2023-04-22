import requests


class RequestError(Exception):
    """
    Exception thrown if a HTTP request operation returned a non-ok code.

    Attributes:
        response -- request response
    """
    def __init__(self, message: str, response: requests.Response):
        self.response = response
        super().__init__(message)
