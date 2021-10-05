import curses

class Toc:
    def __init__(self, stdscr: curses.window, toc: list[tuple[str, int]]) -> None:
        self.stdscr = stdscr
        self.focused = False
        self.selected_chapter = -1
        self.action = ""
        self.toc = toc
        self.padding = 3
        self.y_offset = 0

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

    def action_resize(self) -> None:
        self.action = "resize"
        self.y_offset = 0
        self.focused = False

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
                curses.KEY_RESIZE: self.action_resize,
                }
        action = keys.get(key, self.action_noop)
        action()

    def redraw(self) -> None:
        for row, (label, _) in enumerate(self.toc):
            if self.selected_chapter == row:
                self.pad.addstr(row, self.padding, label, curses.A_REVERSE)
            else:
                self.pad.addstr(row, self.padding, label)
        # calculate offset so that the selected chapter
        # will allways appear on screen.
        num_of_visible_rows = self.rows - 4 * self.padding + 1
        last_visible_row = self.y_offset + num_of_visible_rows - 1
        if self.selected_chapter > last_visible_row:
            self.y_offset = self.selected_chapter - num_of_visible_rows + 1
        elif self.selected_chapter < self.y_offset:
            self.y_offset = self.selected_chapter
        self.pad.refresh(self.y_offset, 0, 2 * self.padding, self.padding + 1, self.rows -  2 * self.padding, self.cols - 2 * self.padding)

    def loop(self, chapter_idx: int) -> tuple[str, int]:
        if not self.toc:
            return "", 0
        # clean previous toc to remove possible broken window
        # will allways throw AttributeError on first loop() call
        try:
            self.window.clear()
        except AttributeError:
            pass
        self.rows, self.cols = self.stdscr.getmaxyx()
        # terminal too small to display toc
        # 17 is the length of "Table of Contents"
        if self.rows - 4 * self.padding + 1 <= 0 or self.cols - 3 * self.padding - 17 <= 0:
            return "", 0
        # create a fixed window with a title and a border which will contain the pad.
        # this is done purely for aesthetic reasons.
        self.window = self.stdscr.subwin(self.rows - self.padding * 2, self.cols - self.padding * 2, self.padding, self.padding)
        self.window.box()
        self.window.addstr(0, self.padding, "Table of Contents", curses.A_BOLD | curses.A_ITALIC)
        self.window.refresh()
        # calculate size of pad, it needs to contain all of the toc.
        longest_row = max([label for label, _ in self.toc], key=len)
        self.pad = curses.newpad(len(self.toc) + self.padding, len(longest_row) + self.padding)
        # the toc is a list of [label, chapter_idx], we know our current chapter_idx
        # with that information we want to know which index to highlight in the toc
        # so first we map out the toc to look like: [False, False, False, ..., True, True, ...]
        # where True means the chapter_idx is too much and it's in the previous False.
        # we then enumerate it and filter out the Falses. then we take the first True.
        # now, as mentioned - Truee means it's too much, so we go back by one.
        # if there's no True, we just take the length of the toc subtracted by one.
        # there's probably a better more readable way to write it, but this seems as fast as it can get.
        self.selected_chapter = next((idx for idx, val in enumerate(map(lambda c: c[1] > chapter_idx, self.toc)) if val), len(self.toc)) - 1
        self.redraw()
        self.focused = True
        while self.focused:
            ch = self.pad.getch()
            self.on_key(ch)
        return self.action, self.toc[self.selected_chapter][1]

