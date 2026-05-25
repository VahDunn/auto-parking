from enum import Enum


class TrackFormat(str, Enum):
    json = "json"
    geojson = "geojson"
