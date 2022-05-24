import curses
import toml
from string import ascii_letters
from typing import Any, TypeVar

T = TypeVar("T")


class Config:
    def __init__(self, path):
        with open(path, "r") as file:
            self._config = toml.load(file)
    
    def _parse_key(self, k) -> int:
        if k in ascii_letters:
            return ord(k)
        elif k.startswith("KEY"):
            if k in curses.__dict__:
                return curses.__dict__[k]
        elif isinstance(k, int):
            return k
        return -1

    def keybinds(self, section) -> dict:
        items = self.get(section, {}).items()
        return {self._parse_key(k): v for k, v in items}

    def get(self, key: str, default: Any | T = None) -> Any | T:
        return self._config.get(key, default)

    @property
    def highlight_color(self) -> tuple[int, int, int]:
        default_hex = "#ff000"
        hex = self.get("highlight_color", default_hex)
        hex = hex.lstrip("#")
        r = int(hex[:2], 16) * 1000 // 256
        g = int(hex[2:4], 16) * 1000 // 256
        b = int(hex[4:6], 16) * 1000 // 256
        return r, g, b
