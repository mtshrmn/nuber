use crate::deunicode::Deunicode;
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

type Head = (usize, usize);
type LinesLengths = Vec<usize>;
type Highlight = (Head, LinesLengths);

#[pymethods]
impl Book {
    #[new]
    fn new(path: String) -> Self {
        let temp_dir = tempdir().unwrap();
        let term_info = Self::get_term_info();
        let mut book = EpubDoc::new(path).unwrap();

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
            .map(|p| {
                (
                    p.label.clone(),
                    self.book.resource_uri_to_chapter(&p.content),
                )
            })
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

    // returns single string with pure text and line lengths
    // TODO: rename function
    fn render_current_chapter_text(&mut self) -> (String, Vec<usize>) {
        let mut lines_len = Vec::new();
        let mut text = String::new();
        let temp_dir = self.temp_dir.path().to_owned();
        let decorator = Decorator::new(temp_dir.as_path(), self.term_info);
        let render_tree = parse(self.get_current_str().as_bytes());
        let lines = render_tree
            .render(self.term_info.col as usize, decorator)
            .into_lines();

        for line in lines {
            let mut line_str = String::new();
            for element in line.iter() {
                if let TaggedLineElement::Str(ts) = element {
                    line_str.push_str(&ts.s.clone());
                }
            }
            let line = line_str.trim_end();
            let line_len = line.chars().count();
            text.push_str(line);
            text.push(' ');
            lines_len.push(line_len + 1);
        }
        (text, lines_len)
    }

    fn highlight_query_in_current_chapter(&mut self, query: &str) -> Vec<Highlight> {
        let mut matches = Vec::new();
        let (text, lines_len) = self.render_current_chapter_text();
        let deunicoded_text = Deunicode::from(text.as_str());
        for range in deunicoded_text.match_indices(|s| s.to_lowercase(), query) {
            let start = range.start;
            let mut col_idx = range.start;
            let mut row_idx = 0;
            for (idx, line_len) in lines_len.clone().into_iter().enumerate() {
                if col_idx < line_len {
                    row_idx = idx;
                    break;
                }
                col_idx -= line_len;
            }
            let first_char = (row_idx, col_idx);
            let mut query_len = range.end - start;
            // create a vec of following lines after the first match
            // each index is the next line with the
            // specified number of characters to highlight.
            // the highlight in the first line starts from `col_idx`
            // in the rest (if exist) of the lines - start from 0.
            let mut lines_len_iter = lines_len.clone().into_iter().skip(row_idx);
            let first_line_len = lines_len_iter.next().unwrap();
            // because the first line is special, we will treat it
            // first and then iterate over the rest.
            let first_highlight = query_len.min(first_line_len - col_idx);
            let mut highlights = Vec::from([first_highlight]);
            // subtract the amount of chars we pushed into `highlights`
            query_len = query_len.saturating_sub(first_highlight);
            // iterate over the rest of the lines
            for line_len in lines_len_iter {
                // if the rest of the highlight can fit into the line
                // we do so and stop iterating. we're done.
                if line_len >= query_len {
                    highlights.push(query_len);
                    break;
                }
                // otherwise, we just enter the line_len and subtract
                highlights.push(line_len);
                query_len = query_len.saturating_sub(line_len);
            }
            matches.push((first_char, highlights));
        }
        matches
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
