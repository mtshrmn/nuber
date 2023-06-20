import curses
from typing import Tuple

class CmdLine:
    def __init__(self, stdscr: curses.window, prompt=":") -> None:
        self.stdscr = stdscr
        self.command = ""
        self.action = ""
        self.prompt = prompt
        self.focused = True

        self.keys = {
                10: self.action_select,                         # key_enter
                13: self.action_select,                         # key_enter
                curses.KEY_ENTER: self.action_select,
                8: self.action_backspace,                       # backspace
                127: self.action_backspace,                     # backspace
                curses.KEY_BACKSPACE: self.action_backspace,
                27: self.action_close,                          # escape
                curses.KEY_RESIZE: self.action_resize,
                }

    def action_select(self) -> None:
        self.action = "select"
        self.focused = False

    def action_close(self) -> None:
        self.action = "close"
        self.focused = False

    def action_backspace(self) -> None:
        if not self.command:
            self.focused = False
        self.command = self.command[:-1]

    def action_resize(self) -> None:
        self.action = "resize"
        self.focused = False

    def on_key(self, key: int) -> None:
        def append_char():
            self.command += chr(key)

        action = self.keys.get(key, append_char)
        action()

    def crop_text(self, text):
        if len(text) + 1 < self.cols:
            return text
        return text[1 - self.cols + 1:]

    def redraw(self) -> None:
        if self.focused == False:
            return
        self.input.clear()
        self.input.addch(0, 0, self.prompt, curses.A_REVERSE)
        # purely for cosmetic reasons
        self.input.addstr(0, 1, " " * (self.cols - 1), curses.A_REVERSE)
        self.input.addstr(0, 1, self.crop_text(self.command), curses.A_REVERSE)
        self.input.refresh()

    def run(self, command="", prompt=":") -> Tuple[str, str]:
        self.prompt = prompt
        self.rows, self.cols = self.stdscr.getmaxyx()
        self.command = command
        self.input = curses.newwin(1, self.cols + 1, self.rows - 1, 0)
        self.input.keypad(True)
        self.focused = True
        self.redraw()

        while self.focused:
            ch = self.input.getch()
            self.on_key(ch)
            self.redraw()
        return self.action, self.command

