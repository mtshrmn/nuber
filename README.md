# nuber

Inspired by [epy](https://github.com/wustho/epy), *nuber* is an Epub terminal reader with inline images written with Rust and Python using [Überzug](https://github.com/seebye/ueberzug).

## Demo

https://user-images.githubusercontent.com/18540571/171234596-08050407-6ee1-45b3-868b-e315de1e7190.mp4


### Features
 - Display images in terminal.
 - Movement with vim keys `hjkl`.
 - Table of content navigation with `t`.
 - Bookmarks (`B` to view, `b` to add)
 - Dynamic window resize.
 - Rememebers last position per book.

### Installation
```sh
$ pip install nuber
```

### Usage
```sh
$ nuber --help
Usage: nuber [OPTIONS] BOOK

Options:
  -c, --config PATH
  --help             Show this message and exit.
```

### Configuration
```toml
# nuber example config file

# there are three possible ways to add a new keybind:
# 1. <ascii letter> = <action>
# 2. KEY_<key> = <action>, see https://docs.python.org/3/library/curses.html#constants
# 3. integer = <action>, where the integer is the character recived from curses.getch()

# currently all <actions> are listed
# those are the default keybinds:

[reader_keybinds]
j = "scroll_down"
k = "scroll_up"
g = "top"
G = "bottom"
l = "next_chapter"
h = "previous_chapter"
t = "open_toc"
B = "open bookmarks"
b = "add_bookmark"
":" = "open_cmd"
q = "quit"
KEY_RESIZE = "resize"

[bookmarks_keybinds]
B = "close_view"
d = "delete_bookmark"
q = "quit"
j = "next"
k = "previous"
o = "select"
10 = "select" # return
13 = "select" # return
KEY_ENTER = "select" 
KEY_RESIZE = "resize"

[toc_keybinds]
t = "close_view"
q = "quit"
j = "next"
k = "previous"
o = "select"
10 = "select" # return
13 = "select" # return
KEY_ENTER = "select" 
KEY_RESIZE = "resize"

```

### Contribute
Requirements: `maturin`, `poetry`
```sh
$ git clone https://github.com/mtshrmn/nuber.git --recursive && cd nuber
$ cd rust-html2text && git apply ../html2text.patch && cd ..
$ poetry install && poetry shell
$ maturin develop && exit
$ poetry run nuber
```
