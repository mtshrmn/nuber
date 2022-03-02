import curses
import json
import appdirs
import os
import ueberzug.lib.v0 as ueberzug
from .rust_module.nuber import Book, Image
from .toc import Toc
from .bookmarks import Bookmark
from .cmdline import CmdLine
from .config import Config


class Reader:
    def __init__(self, path: str, config_path=None) -> None:
        # curses init
        self.path = os.path.abspath(path)
        self.stdscr: curses.window = curses.initscr()
        self.rows, self.cols = self.stdscr.getmaxyx()

        curses.noecho()
        curses.curs_set(0)
        curses.set_escdelay(1) # type: ignore

        # read configuration file
        config_dir = config_path
        if config_path == None:
            config_dir = os.path.join(appdirs.user_config_dir(), "nuber")
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)
        config_file_path = os.path.join(config_dir, "config.toml")
        if not os.path.exists(config_file_path):
            with open(config_file_path, "x"):
                pass

        self.config = Config(config_file_path)

        self.cache_dir = self.config.get("cache_dir")
        if self.cache_dir is None:
            self.cache_dir = os.path.join(appdirs.user_cache_dir(), "nuber")

        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)
        self.state_file = os.path.join(self.cache_dir, "state.json")
        self.book = Book(self.path)
        self.lines = self.book.number_of_lines()

        self.offset = 0
        self.current_position = 0
        self.chapter_idx = 0
        self.positions = [0] * self.book.get_num_chapters()
        self.placements = {}
        self.current_chapter_placements = []
        self.word_count_per_line = []
        self.bookmarks = Bookmark(self.stdscr, keybinds=self.config.keybinds("bookmarks_keybinds"))

        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as state_file:
                states = json.loads(state_file.read())
                try:
                    state = states[self.path]
                    self.positions = state["positions"]
                    self.chapter_idx = state["chapter_idx"]
                    self.bookmarks.load_bookmarks(state["bookmarks"])
                    self.current_position = self.positions[self.chapter_idx]
                    self.book.set_current_chapter(self.chapter_idx)
                except KeyError:
                    pass

        self.toc = Toc(self.stdscr, self.book.get_toc(), keybinds=self.config.keybinds("toc_keybinds"))
        self.cmdline = CmdLine(self.stdscr)

    def add_image(self, canvas: ueberzug.Canvas, position: tuple[int, int], info: Image) -> None:
        img_id = f"{position[0]}{position[1]}{info.path}"
        if img_id in self.placements:
            placement = self.placements[img_id]
        else:
            placement = canvas.create_placement(img_id)
            placement.path = info.path
            self.placements[img_id] = placement
        placement.x, placement.y = position
        placement.width, placement.height = info.size
        self.current_chapter_placements.append((position[1], placement))

    def render_chapter(self, canvas: ueberzug.Canvas) -> None:
        chapter = self.book.render_current_chapter()
        self.chapter_rows = max(self.rows, len(chapter))
        self.pad: curses.window = curses.newpad(self.chapter_rows, self.cols)
        self.percentage_win = curses.newwin(1, 10, 0, self.cols - 4)
        self.word_count_per_line = []
        for line_num, elements in enumerate(chapter):
            current_pos = 0
            word_count = 0
            for element in elements:
                if info := element.image_info:
                    if element.text.startswith("S"):
                        self.add_image(canvas, (current_pos, line_num), info)
                    current_pos += len(element.text)
                else:
                    current_pos += self.addstr(line_num, current_pos, element.text, element.style)
                word_count += len(element.text.split())
            self.word_count_per_line.append(max(1, word_count))

    def determine_visibility(self, y: int, h: int) -> ueberzug.Visibility:
        y_pos = y - self.offset
        padding = 1
        if y_pos + h + padding < 0:
            return ueberzug.Visibility.INVISIBLE
        if y_pos - padding > self.rows:
            return ueberzug.Visibility.INVISIBLE
        return ueberzug.Visibility.VISIBLE

    def addstr(self, y: int, x: int, text: str, styles: list) -> int:
        formatting = curses.A_NORMAL
        for style in styles:
            if style == "bold":
                formatting = formatting | curses.A_BOLD
            elif style == "italic":
                formatting = formatting | curses.A_ITALIC
            elif style == "reverse":
                formatting = formatting | curses.A_REVERSE
            elif style == "underline":
                formatting = formatting | curses.A_UNDERLINE

        try:
            self.pad.addstr(y, x, text, formatting)
            return len(text)
        except curses.error:
            return 0

    def update_offset(self) -> None:
        self.offset = 0
        while self.current_position > sum(self.word_count_per_line[:self.offset]):
            self.offset += 1

    def update_progress(self) -> None:
        self.progress = sum(self.lines[:max(0, self.chapter_idx - 1)]) + self.offset + self.rows

    @staticmethod
    def action_noop(_: ueberzug.Canvas) -> None:
        pass

    def action_scroll_down(self, canvas: ueberzug.Canvas) -> None:
        if self.offset < self.chapter_rows - self.rows:
            self.offset += 1
            self.progress += 1
            self.current_position = sum(self.word_count_per_line[:self.offset])
            self.redraw(canvas)

    def action_scroll_up(self, canvas: ueberzug.Canvas) -> None:
        if self.offset > 0:
            self.offset -= 1
            self.progress -= 1
            self.current_position = sum(self.word_count_per_line[:self.offset])
            self.redraw(canvas)

    def action_top(self, canvas: ueberzug.Canvas) -> None:
        self.progress -= self.offset
        self.offset = 0
        self.current_position = 0
        self.redraw(canvas)

    def action_bottom(self, canvas: ueberzug.Canvas) -> None:
        # remove offset from progrss, as if calculating progress from the 1st line
        self.progress -= self.offset
        self.offset = self.chapter_rows - self.rows
        # add newly calculated offset for bottom of chapter
        self.progress += self.offset
        self.current_position = sum(self.word_count_per_line[:self.offset])
        self.redraw(canvas)

    def action_next_chapter(self, canvas: ueberzug.Canvas) -> None:
        if self.book.next_chapter():
            self.positions[self.chapter_idx] = self.current_position
            self.chapter_idx += 1
            self.clear(canvas)
            self.current_position = self.positions[self.chapter_idx]
            self.render_chapter(canvas)
            self.progress -= self.offset
            self.update_offset()
            self.progress += self.lines[self.chapter_idx - 2] + self.offset
            self.redraw(canvas)

    def action_previous_chapter(self, canvas: ueberzug.Canvas) -> None:
        if self.book.previous_chapter():
            self.positions[self.chapter_idx] = self.current_position
            self.progress -= self.offset + self.lines[self.chapter_idx - 2]
            self.chapter_idx -= 1
            self.clear(canvas)
            self.current_position = self.positions[self.chapter_idx]
            self.render_chapter(canvas)
            self.update_offset()
            self.progress += self.offset
            self.redraw(canvas)

    def action_open_toc(self, canvas: ueberzug.Canvas) -> None:
        self.hide_current_placements(canvas)
        action, chapter = self.toc.run(self.chapter_idx)
        if action == "quit":
            self.action_quit(canvas)
        elif action == "select":
            self.positions[self.chapter_idx] = self.current_position
            self.chapter_idx = chapter
            self.clear(canvas)
            self.current_position = 0
            self.book.set_current_chapter(self.chapter_idx)
            self.render_chapter(canvas)
            self.update_offset()
            self.redraw(canvas)
        elif action == "resize":
            self.action_resize(canvas)
        else:
            self.redraw(canvas)

    def action_open_bookmarks(self, canvas: ueberzug.Canvas) -> None:
        self.hide_current_placements(canvas)
        position = self.chapter_idx, self.current_position
        action, bookmark = self.bookmarks.run(position)
        if action == "quit":
            self.action_quit(canvas)
        elif action == "select":
            self.positions[self.chapter_idx] = self.current_position
            self.clear(canvas)
            self.chapter_idx, self.current_position = bookmark
            self.book.set_current_chapter(self.chapter_idx)
            self.render_chapter(canvas)
            self.update_offset()
            self.redraw(canvas)
        elif action == "resize":
            self.action_resize(canvas)
        else:
            self.redraw(canvas)

    def action_add_bookmark(self, canvas: ueberzug.Canvas) -> None:
        self.action_open_cmd(canvas, command="bookmark add ")

    def action_open_cmd(self, canvas: ueberzug.Canvas, command="") -> None:
        self.hide_current_placements(canvas)
        command = self.cmdline.run(command=command)
        # system commands:
        if command == "resize":
            self.action_resize(canvas)
            return

        tokens = command.split()
        if len(tokens) > 2 and tokens[0] == "bookmark" and tokens[1] == "add":
            if label := "".join(tokens[2:]):
                position = self.chapter_idx, self.current_position
                self.bookmarks.add_bookmark(label, position)
        # TODO: add indication for unkown command
        self.redraw(canvas)

    def action_quit(self, _) -> None:
        self.positions[self.chapter_idx] = self.current_position
        states = {}
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as state_file:
                states = json.loads(state_file.read())

        states[self.path] = {
                "positions": self.positions,
                "chapter_idx": self.chapter_idx,
                "bookmarks": self.bookmarks.data,
                }

        with open(self.state_file, "w") as state_file:
            state_file.write(json.dumps(states))
        curses.endwin()
        exit(0)

    def action_resize(self, canvas: ueberzug.Canvas) -> None:
        self.clear(canvas)
        self.book.update_term_info()
        self.rows, self.cols = self.stdscr.getmaxyx()
        self.lines = self.book.number_of_lines()
        self.update_progress()
        self.render_chapter(canvas)
        self.update_offset()
        self.redraw(canvas)

    def on_key(self, key: int, canvas: ueberzug.Canvas) -> None:
        keys = {
                ord("h"): self.action_previous_chapter,
                ord("j"): self.action_scroll_down,
                ord("k"): self.action_scroll_up,
                ord("l"): self.action_next_chapter,
                ord("q"): self.action_quit,
                ord("G"): self.action_bottom,
                ord("g"): self.action_top,
                ord("t"): self.action_open_toc,
                ord(":"): self.action_open_cmd,
                ord("B"): self.action_open_bookmarks,
                ord("b"): self.action_add_bookmark,
                curses.KEY_RESIZE: self.action_resize,
                }

        reader_keybinds = self.config.keybinds("reader_keybinds").items()
        custom_keys = {k: getattr(self, f"action_{v}", self.action_noop) for k, v, in reader_keybinds}
        keys.update(custom_keys)
        action = keys.get(key, self.action_noop)
        action(canvas)

    def clear(self, canvas: ueberzug.Canvas) -> None:
        try:
            self.pad.clear()
            self.percentage_win.clear()
            with canvas.synchronous_lazy_drawing:
                for _, placement in self.current_chapter_placements:
                    placement.visibility = ueberzug.Visibility.INVISIBLE
            self.current_chapter_placements = []
        except AttributeError:
            pass

    def hide_current_placements(self, canvas: ueberzug.Canvas) -> None:
        with canvas.synchronous_lazy_drawing:
            for _, placement in self.current_chapter_placements:
                placement.visibility = ueberzug.Visibility.INVISIBLE


    def redraw(self, canvas: ueberzug.Canvas) -> None:
        if self.offset > (offset := self.chapter_rows - self.rows):
            self.offset = offset
        self.pad.refresh(self.offset, 0, 0, 0, self.rows - 1, self.cols - 1)

        percentage_str = f"{self.progress * 100 // sum(self.lines)}%"
        self.percentage_win.addstr(0, 4 - len(percentage_str), percentage_str, curses.A_BOLD)
        self.percentage_win.refresh()
        with canvas.synchronous_lazy_drawing:
            for initial_y, placement in self.current_chapter_placements:
                visibility = self.determine_visibility(initial_y, placement.height)
                if visibility == ueberzug.Visibility.VISIBLE:
                    placement.y = initial_y - self.offset
                placement.visibility = visibility

    @ueberzug.Canvas()
    def loop(self, canvas: ueberzug.Canvas) -> None:
        self.render_chapter(canvas)
        self.update_offset()
        self.update_progress()
        self.redraw(canvas)
        while True:
            ch = self.pad.getch()
            self.on_key(ch, canvas)
