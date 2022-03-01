import curses
from .listview import ListView

class Bookmark(ListView):
    def __init__(self, stdscr: curses.window, keybinds={}) -> None:
        keys = {
                ord("B"): "close_view",
                ord("d"): "delete_bookmark",
                }
        keys.update(keybinds)
        super().__init__(stdscr, [], keybinds=keys)
        self.title = "Bookmarks"

    def determine_selected_row(self, bookmark_position: tuple[int, int]) -> int:
        chapter_idx, position = bookmark_position
        def compare_pos(other_bookmark: tuple[str, tuple[int, int]]):
            other_idx, other_pos = other_bookmark[1]
            if other_idx == chapter_idx:
                return other_pos > position
            return other_idx > chapter_idx

        return next((idx for idx, val in enumerate(map(compare_pos, self.data)) if val), len(self.data)) - 1

    def load_bookmarks(self, bookmarks: list[tuple[str, tuple[int, int]]]) -> None:
        self.data = bookmarks

    def add_bookmark(self, label: str, position: tuple[int, int]) -> None:
        index = self.determine_selected_row(position) + 1
        while label in map(lambda b: b[0], self.data):
            label = f"{label}_"
        self.data.insert(index, (label, position))

    def action_delete_bookmark(self) -> None:
        if not self.data:
            return
        label = self.data[self.selected_row][0]
        action, selection = Confirmation(self.stdscr, label).run(None)
        if action == "quit":
            self.action_quit()
            return
        if action == "resize":
            self.action_resize()
            return
        if action == "select" and selection == 0:
            self.pad.clear()
            del self.data[self.selected_row]
            self.selected_row = max(0, self.selected_row - 1)
        self.redraw_border()
        self.redraw()


class Confirmation(ListView):
    def __init__(self, stdscr: curses.window, item: str) -> None:
        super().__init__(stdscr, [("Yes", 0), ("No", 1)])
        self.title = f"Delete bookmark \"{item}\"?"
        _, cols = self.stdscr.getmaxyx()
        max_size = cols - 3 * self.padding - 1
        if len(self.title) > max_size: 
            self.title = self.title[:max_size - 5] + "...\"?"
