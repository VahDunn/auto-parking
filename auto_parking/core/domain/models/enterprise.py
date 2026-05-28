from dataclasses import dataclass, field

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class EnterpriseModel(DomainModel):
    id: int
    name: str
    settlement: str
    vehicles: list[int] = field(default_factory=list)
    drivers: list[int] = field(default_factory=list)
    managers: list[int] = field(default_factory=list)
    timezone: str | None = None
