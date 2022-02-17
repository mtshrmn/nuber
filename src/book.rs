use crate::parser::{Converter, Decorator, Element, RichConverter, Style};
use epub::doc::EpubDoc;
use html2text::parse;
use html2text::render::text_renderer::TaggedLineElement;
use libc::{c_ushort, ioctl, STDOUT_FILENO, TIOCGWINSZ};
use pyo3::prelude::*;
use std::fs::{write, File};
use std::mem;
use tempfile::{tempdir, TempDir};

#[pyclass]
#[derive(Copy, Clone)]
pub struct TermSize {
    pub row: c_ushort,
    pub col: c_ushort,
    pub x: c_ushort,
    pub y: c_ushort,
}

#[pyclass]
pub struct Book {
    book: EpubDoc<File>,
    temp_dir: TempDir,
    term_info: TermSize,
}

#[pymethods]
impl Book {
    #[new]
    fn new(path: String) -> Self {
        let temp_dir = tempdir().unwrap();
        let term_info = Self::get_term_info();
        let mut book = EpubDoc::new(path.clone()).unwrap();

        for (_, (path, mime)) in book.resources.clone() {
            if mime.contains("image") {
                let fname = path.file_name().unwrap();
                let image_data = book.get_resource_by_path(path.clone()).unwrap();
                write(temp_dir.path().join(fname), image_data).unwrap();
            }
        }

        Book {
            book,
            temp_dir,
            term_info,
        }
    }

    #[staticmethod]
    fn get_term_info() -> TermSize {
        unsafe {
            let mut size: TermSize = mem::zeroed();
            ioctl(STDOUT_FILENO, TIOCGWINSZ, &mut size as *mut _);
            size
        }
    }

    fn update_term_info(&mut self) {
        self.term_info = Self::get_term_info();
    }

    fn next_chapter(&mut self) -> bool {
        self.book.go_next().is_ok()
    }

    fn previous_chapter(&mut self) -> bool {
        self.book.go_prev().is_ok()
    }

    fn get_current_str(&mut self) -> String {
        self.book.get_current_str().unwrap()
    }

    fn set_current_chapter(&mut self, chapter: usize) -> bool {
        self.book.set_current_page(chapter).is_ok()
    }

    fn get_num_chapters(&mut self) -> usize {
        self.book.get_num_pages()
    }

    fn get_toc(&mut self) -> Vec<(String, usize)> {
        self.book
            .toc
            .iter()
            .map(|p| (p.label.clone(), self.book.resource_uri_to_chapter(&p.content)))
            .filter(|(_, n)| n.is_some())
            .map(|(l, n)| (l, n.unwrap()))
            .collect()
    }

    fn number_of_lines(&mut self) -> Vec<usize> {
        let current_chapter = self.book.get_current_page();
        self.set_current_chapter(0);

        let temp_dir = self.temp_dir.path().to_owned();
        let decorator = Decorator::new(temp_dir.as_path(), self.term_info);

        let mut number_of_lines = Vec::new();

        // iterate over all of the chapters and sum up the lines
        while self.next_chapter() {
            let render_tree = parse(self.get_current_str().as_bytes());
            let lines = render_tree
                .render(self.term_info.col as usize, decorator)
                .into_lines();
            number_of_lines.push(lines.len());
        }
        self.set_current_chapter(current_chapter);
        number_of_lines
    }

    fn render_current_chapter(&mut self) -> Vec<Vec<Element>> {
        let mut doc = Vec::new();
        let rich_converter = RichConverter;
        let temp_dir = self.temp_dir.path().to_owned();
        let decorator = Decorator::new(temp_dir.as_path(), self.term_info);
        let render_tree = parse(self.get_current_str().as_bytes());
        let lines = render_tree
            .render(self.term_info.col as usize, decorator)
            .into_lines();

        for line in lines {
            let mut elements = Vec::new();
            for element in line.iter() {
                if let TaggedLineElement::Str(ts) = element {
                    let styles: Vec<_> = ts
                        .tag
                        .iter()
                        .filter_map(|a| rich_converter.get_style(a))
                        .collect();
                    let link_target = ts
                        .tag
                        .iter()
                        .find_map(|a| rich_converter.get_link(a))
                        .map(ToOwned::to_owned);
                    let image_info = ts.tag.iter().find_map(|a| decorator.get_image_info(a));
                    elements.push(Element::new(
                        ts.s.clone(),
                        Style::merge(&styles),
                        link_target,
                        image_info,
                    ));
                }
            }
            doc.push(elements);
        }
        doc
    }
}
