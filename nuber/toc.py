import curses
from .listview import ListView

class Toc(ListView):
    def __init__(self, stdscr: curses.window, toc: list[tuple[str, int]]) -> None:
        super().__init__(stdscr, toc)
        self.title = "Table of Contents"
        self.keys = {ord("t"): self.action_close_view}

    def determine_selected_row(self, chapter_idx) -> int:
        return next((idx for idx, val in enumerate(map(lambda c: c[1] > chapter_idx, self.data)) if val), len(self.data)) - 1
