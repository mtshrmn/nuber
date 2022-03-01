import curses
from .listview import ListView

class Toc(ListView):
    def __init__(self, stdscr: curses.window, toc: list[tuple[str, int]], keybinds={}) -> None:
        keys = {ord("t"): "close_view"}
        keys.update(keybinds)
        super().__init__(stdscr, toc, keybinds=keys)
        self.title = "Table of Contents"

    def determine_selected_row(self, chapter_idx) -> int:
        return next((idx for idx, val in enumerate(map(lambda c: c[1] > chapter_idx, self.data)) if val), len(self.data)) - 1
