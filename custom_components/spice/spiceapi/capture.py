from .connection import Connection
from .request import Request
import base64


def capture_get_screens(con: Connection):
    """Return the list of available screen IDs on the host."""
    return con.request(Request("capture", "get_screens")).get_data()


def capture_get_jpg(con: Connection, screen: int = 0, quality: int = 60, divide: int = 1):
    """Grab a single JPEG frame from the given screen.

    :param screen: screen ID (see :func:`capture_get_screens`)
    :param quality: JPEG quality (0-100)
    :param divide: downscale factor (1 = full resolution, 2 = half, ...)
    :return: dict with ``timestamp``, ``width``, ``height`` and decoded ``jpeg``
             bytes, or ``None`` if the host returned no frame.
    """
    req = Request("capture", "get_jpg")
    req.add_param(screen)
    req.add_param(quality)
    req.add_param(divide)

    # response data: [timestamp, width, height, base64_jpeg]
    data = con.request(req).get_data()
    if len(data) < 4:
        return None
    return {
        "timestamp": data[0],
        "width": data[1],
        "height": data[2],
        "jpeg": base64.b64decode(data[3]),
    }
