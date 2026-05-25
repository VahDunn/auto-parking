from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class DomainModel:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
