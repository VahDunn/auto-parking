import os
from typing import TYPE_CHECKING

from auto_parking.infrastructure.geocoding.geoapify import GeoapifyReverseGeocoder

if TYPE_CHECKING:
    from auto_parking.app.ports.geocoding import ReverseGeocoder

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "")


def get_reverse_geocoder() -> "ReverseGeocoder | None":
    if not GEOAPIFY_API_KEY:
        return None
    return GeoapifyReverseGeocoder(api_key=GEOAPIFY_API_KEY)
