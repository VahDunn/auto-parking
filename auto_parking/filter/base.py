from dataclasses import dataclass


@dataclass(slots=True)
class BaseFilter:
    load_relations: bool = True
