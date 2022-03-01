import curses
import toml
from string import ascii_letters


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

    def keybinds(self, section):
        items = self._config.get(section, {}).items()
        return {self._parse_key(k): v for k, v in items}

    def get(self, key, **kw):
        return self._config.get(key, **kw)
