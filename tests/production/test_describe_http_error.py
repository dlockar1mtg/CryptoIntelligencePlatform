import requests

from crypto_platform.platform import describe_http_error


class _Response:
    def __init__(self, status, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


def test_http_error_shows_status_and_provider_message():
    exc = requests.HTTPError("400 Client Error for url: https://example.test/obs?series_id=X&api_key=SYNTHKEY")
    exc.response = _Response(400, {"error_code": 400, "error_message": "Bad Request. The value for variable api_key is not registered."})
    text = describe_http_error(exc)
    assert text.startswith("HTTP 400: Bad Request.") and "SYNTHKEY" not in text


def test_connection_error_has_query_strings_removed():
    exc = requests.ConnectionError("Max retries exceeded with url: /fred/series/observations?series_id=X&api_key=SYNTHKEY")
    text = describe_http_error(exc)
    assert "ConnectionError" in text and "SYNTHKEY" not in text and "?..." in text


def test_non_json_body_and_none():
    exc = requests.HTTPError("503")
    exc.response = _Response(503, None, "<html>Service Unavailable</html>")
    assert describe_http_error(exc).startswith("HTTP 503: <html>Service Unavailable")
    assert describe_http_error(None) == "no response"
