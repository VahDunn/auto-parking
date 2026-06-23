from collections.abc import Sequence
from typing import Protocol


class ManagerLookup(Protocol):
    async def manager_ids_for_enterprise(self, enterprise_id: int) -> Sequence[int]:
        pass
