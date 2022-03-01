import curses
from typing import Any

class ListView:
    def __init__(self, stdscr: curses.window, data: list[tuple[str, Any]], keybinds={}) -> None:
        # settings
        self.padding = 3
        self.title = "title"
        self.keys = {k: getattr(self, f"action_{v}", self.action_noop) for k, v in keybinds.items()}

        # context
        self.stdscr = stdscr
        self.data = data

        # state
        self.focused = False
        self.selected_row = 0
        self.action = ""
        self.y_offset = 0

    def action_noop(self) -> None:
        pass

    def action_quit(self) -> None:
        # quit main window and not just the ListView
        self.action = "quit"
        self.focused = False

    def action_close_view(self) -> None:
        # close the ListView but keep the main window running
        self.action = "close"
        self.focused = False

    def action_select(self) -> None:
        if self.data:
            self.action = "select"
            self.focused = False

    def action_next(self) -> None:
        if self.selected_row < len(self.data) - 1:
            self.selected_row += 1
            self.redraw()

    def action_previous(self) -> None:
        if self.selected_row > 0:
            self.selected_row -= 1
            self.redraw()

    def action_resize(self) -> None:
        # close the ListView and request main window to resize itself according to new dimensions
        self.action = "resize"
        self.y_offset = 0
        self.focused = False

    def on_key(self, key: int) -> None:
        keys = {
                ord("q"): self.action_quit,
                ord("j"): self.action_next,
                ord("k"): self.action_previous,
                ord("o"): self.action_select,
                10: self.action_select,                 # key_enter
                13: self.action_select,                 # key_enter
                curses.KEY_ENTER: self.action_select,   # key_enter
                curses.KEY_RESIZE: self.action_resize,
                }
        keys.update(self.keys)
        action = keys.get(key, self.action_noop)
        action()

    def redraw(self) -> None:
        padding = self.padding
        # will allways run after the run() function is called
        for row, (label, _) in enumerate(self.data):
            formatting = curses.A_REVERSE if self.selected_row == row else curses.A_NORMAL
            self.pad.addstr(row, padding, label, formatting)
        # calculate the offset so that the selected row
        # will allways appear on screen.
        num_of_visible_rows = self.rows - 4 * padding + 1
        last_visible_row = self.y_offset + num_of_visible_rows - 1
        if self.selected_row > last_visible_row:
            self.y_offset = self.selected_row - num_of_visible_rows + 1
        elif self.selected_row < self.y_offset:
            self.y_offset = self.selected_row
        self.pad.refresh(self.y_offset, 0, 2 * padding, padding + 1, self.rows - 2 * padding, self.cols - 2 * padding)

    def redraw_border(self) -> None:
        self.border.clear()
        self.border.box()
        self.border.addstr(0, self.padding, self.title, curses.A_BOLD | curses.A_ITALIC)
        self.border.refresh()

    def determine_selected_row(self, _: Any) -> int:
        # inherited classes should implement this method
        return 0

    def has_draw_estate(self) -> bool:
        return self.rows - 4 * self.padding + 1 > 0 and self.cols - 3 * self.padding > len(self.title)

    def run(self, data: Any) -> tuple[str, Any]:
        # clear previously drawn window to remove possible clutter
        # will allways throw AttributeError on first run() call
        try:
            self.border.clear()
        except AttributeError:
            pass
        self.rows, self.cols = self.stdscr.getmaxyx()
        if not self.has_draw_estate():
            return "", 0
        padding = self.padding
        self.border = self.stdscr.subwin(self.rows - 2 * padding, self.cols - 2 * padding, padding, padding)
        self.redraw_border()
        # calculate size of pad, need to contain all of the data.
        longest_row = max([label for label, _ in self.data], key=len) if self.data else ""
        self.pad = curses.newpad(len(self.data) + padding, len(longest_row) + padding)
        self.selected_row = max(0, self.determine_selected_row(data))
        self.redraw()
        self.focused = True
        while self.focused:
            ch = self.pad.getch()
            self.on_key(ch)
        if self.data:
            return self.action, self.data[self.selected_row][1]
        return self.action, None


