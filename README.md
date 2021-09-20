# nuber

Inspired by [epy](https://github.com/wustho/epy), *nuber* is an Epub terminal reader with inline images written with Rust and Python using [Überzug](https://github.com/seebye/ueberzug). Currently in its early stages, *nuber* has simple `hjkl` navigation and is very limited in its features.

![title](screenshot.png)
Book credit: [Humble Pi](https://www.amazon.com/Humble-Pi-When-Wrong-World/dp/0593084683) (by Matt Parker)

### Installation
Requirements: `maturin`, `pip`
```sh
$ git clone https://github.com/mtshrmn/nuber.git --recursive
$ cd rust-html2text && git apply ../html2text.path && cd ..
$ maturin build --release
$ pip install .
```

### Usage
```sh
$ nuber --help
Usage: nuber [OPTIONS] BOOK

Options:
  --help  Show this message and exit.
```
