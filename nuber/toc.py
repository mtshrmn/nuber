import curses

class Toc:
    def __init__(self, stdscr: curses.window, toc: list[tuple[str, int]]) -> None:
        rows, cols = stdscr.getmaxyx()
        self.pad = stdscr.subpad(rows - 4, cols - 8, 2, 4)
        self.pad.box()
        self.pad.addstr(0, cols // 2 - 12, "Table of Contents", curses.A_BOLD | curses.A_ITALIC)
        self.focused = False
        self.selected_chapter = -1
        self.action = ""
        self.toc = toc

        self.redraw()

    def action_noop(self) -> None:
        pass

    def action_quit(self) -> None:
        self.action = "quit"
        self.focused = False

    def action_close_toc(self) -> None:
        self.action = "close_toc"
        self.focused = False

    def action_goto(self) -> None:
        self.action = "goto"
        self.focused = False

    def action_next(self) -> None:
        if self.selected_chapter < len(self.toc) - 1:
            self.selected_chapter += 1
            self.redraw()

    def action_previous(self) -> None:
        if self.selected_chapter > 0:
            self.selected_chapter -= 1
            self.redraw()

    def on_key(self, key: int) -> None:
        keys = {
                ord("q"): self.action_quit,
                ord("t"): self.action_close_toc,
                ord("j"): self.action_next,
                ord("k"): self.action_previous,
                ord("o"): self.action_goto,
                10: self.action_goto, # key_enter
                13: self.action_goto, # key_enter
                curses.KEY_ENTER: self.action_goto, # key_enter
                }
        action = keys.get(key, self.action_noop)
        action()

    def redraw(self) -> None:
        for row, (label, _) in enumerate(self.toc):
            if self.selected_chapter == row:
                self.pad.addstr(row + 2, 3, label, curses.A_REVERSE)
            else:
                self.pad.addstr(row + 2, 3, label)

    def loop(self, chapter_idx: int) -> tuple[str, int]:
        # the toc is a list of [label, chapter_idx], we know our current chapter_idx
        # with that information we want to know which index to highlight in the toc
        # so first we map out the toc to look like: [True, True, True, ..., False, False, ...]
        # where False means the chapter_idx is too much and it's in the previous True.
        # we then enumerate it and filter out the True's. then we take the first False.
        # now, as mentioned - False means it's too much, so we go back by one.
        # if there's no False, we just take the length of the toc subtracted by one.
        # there's probably a better more readable way to write it, but this seems as fast as it can get.
        self.selected_chapter = next((idx for idx, val in enumerate(map(lambda c: c[1] > chapter_idx, self.toc)) if val), len(self.toc)) - 1
        self.redraw()
        self.focused = True
        while self.focused:
            ch = self.pad.getch()
            self.on_key(ch)
        return self.action, self.toc[self.selected_chapter][1]

