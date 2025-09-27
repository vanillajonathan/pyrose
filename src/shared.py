from dataclasses import dataclass


@dataclass(frozen=True)
class Lang:
    name: str
    highlight: str
    extension: str
    interpreter: str
    args: list[str]
