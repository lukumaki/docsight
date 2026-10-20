"""Built-in CH7465 driver extension for optional bounded native-log reads."""

from __future__ import annotations

from app.drivers.ch7465 import CH7465Driver
from .parser import MAX_XML_BYTES, parse_network_log


class CH7465NativeLogDriver(CH7465Driver):
    """Keep standard authentication and data methods; add fun=13 on demand."""

    def get_native_events(self):
        response = self._session.post(
            f"{self._url}/xml/getter.xml",
            data=({"fun": "13"} if self._is_play is False else {
                "token": self._session.cookies.get("sessionToken", ""), "fun": "13"
            }),
            timeout=10,
            allow_redirects=False,
            stream=True,
        )
        try:
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_content(65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_XML_BYTES:
                    raise ValueError("Network Log response exceeds configured size limit")
                chunks.append(chunk)
            return parse_network_log(b"".join(chunks))
        finally:
            response.close()
