import curses
import ueberzug.lib.v0 as ueberzug
from target.release.libnuber import Book


class Reader:
    def __init__(self, path: str) -> None:
        self.stdscr: curses.window = curses.initscr()
        self.rows, self.cols = self.stdscr.getmaxyx()
        curses.noecho()
        curses.curs_set(0)

        self.rounded_offset = 0
        self.precise_offset = 0
        self.chapter_idx = 0
        self.offsets = [self.precise_offset]
        self.placements = {}
        self.current_chapter_placements = []

        self.book = Book(path)

    def render_chapter(self, canvas: ueberzug.Canvas) -> None:
        chapter = self.book.render_current_chapter()
        self.chapter_rows = len(chapter)
        self.pad: curses.window = curses.newpad(self.chapter_rows, self.cols)
        for line_num, elements in enumerate(chapter):
            current_pos = 0
            for element in elements:
                if info := element.image_info:
                    if element.text.startswith("S"):
                        image_id = f"{current_pos}{line_num}{info.path}"
                        try:
                            image = canvas.create_placement(image_id,
                                    x=current_pos, y=line_num, height=info.size[1])
                            self.placements[image_id] = image
                        except ValueError:
                            image = self.placements[image_id]
                            image.x = current_pos
                            image.y = line_num
                            image.width, image.height = info.size
                        self.current_chapter_placements.append((line_num,image))
                        image.path = info.path
                        image.visibility = ueberzug.Visibility.VISIBLE
                    current_pos += len(element.text)
                    continue
                current_pos += self.addstr(line_num, current_pos, element.text, element.style)

        self.redraw(canvas)

    def determine_visibility(self, y: int, h: int) -> ueberzug.Visibility:
        y_pos = y - self.rounded_offset
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

    def on_key(self, key: int, canvas: ueberzug.Canvas) -> None:
        if key == ord("j"):
            if self.rounded_offset < self.chapter_rows - self.rows:
                self.precise_offset += self.cols
                self.rounded_offset = self.precise_offset // self.cols
                self.redraw(canvas)
        elif key == ord("k"):
            if self.rounded_offset > 0:
                self.precise_offset -= self.cols
                self.rounded_offset = self.precise_offset // self.cols
                self.redraw(canvas)
        elif key == ord("l"):
            if self.book.next_chapter():
                self.offsets[self.chapter_idx] = self.precise_offset
                self.chapter_idx += 1
                self.clear(canvas)
                self.redraw(canvas)
                try:
                    self.precise_offset = self.offsets[self.chapter_idx]
                except IndexError:
                    self.precise_offset = 0
                    self.offsets.append(0)
                finally:
                    self.rounded_offset = self.precise_offset // self.cols
                self.render_chapter(canvas)
        elif key == ord("h"):
            if self.book.previous_chapter():
                self.offsets[self.chapter_idx] = self.precise_offset
                self.chapter_idx -= 1
                self.clear(canvas)
                self.redraw(canvas)
                self.precise_offset = self.offsets[self.chapter_idx]
                self.rounded_offset = self.precise_offset // self.cols
                self.render_chapter(canvas)
        elif key == curses.KEY_RESIZE:
            previous_cols = self.cols
            self.rows, self.cols = self.stdscr.getmaxyx()
            self.book.update_term_info()
            self.clear(canvas)
            # make sure that: precise_offset ∈ [0, (chapter_rows - rows) * cols]
            self.precise_offset = max(0, min(self.precise_offset * previous_cols // self.cols, (self.chapter_rows - self.rows) * self.cols))
            self.rounded_offset = self.precise_offset // self.cols
            self.render_chapter(canvas)
        elif key == ord("q"):
            curses.endwin()
            exit(0)

    def clear(self, canvas: ueberzug.Canvas) -> None:
        try:
            self.pad.clear()
            with canvas.synchronous_lazy_drawing:
                for _, placement in self.current_chapter_placements:
                    placement.visibility = ueberzug.Visibility.INVISIBLE
            self.current_chapter_placements = []
        except AttributeError:
            pass

    def redraw(self, canvas: ueberzug.Canvas) -> None:
        self.pad.refresh(self.rounded_offset, 0, 0, 0, self.rows - 1, self.cols)
        with canvas.synchronous_lazy_drawing:
            for initial_y, placement in self.current_chapter_placements:
                visibility = self.determine_visibility(initial_y, placement.height)
                if visibility == ueberzug.Visibility.VISIBLE:
                    placement.y = initial_y - self.rounded_offset
                placement.visibility = visibility

    @ueberzug.Canvas()
    def loop(self, canvas: ueberzug.Canvas) -> None:
        self.render_chapter(canvas)
        while True:
            ch = self.pad.getch()
            self.on_key(ch, canvas)
