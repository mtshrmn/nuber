#![allow(non_snake_case)]

use crate::book::TermSize;
use crate::image::Image;
use enumset::{enum_set, EnumSet, EnumSetType};
use html2text::render::text_renderer::{RichAnnotation, TaggedLine, TextDecorator};
use pyo3::prelude::*;
use std::iter::FromIterator;
use std::path::Path;

#[derive(EnumSetType, Debug)]
pub enum Effect {
    Reverse,
    Underline,
    Italic,
    Bold,
    Strikethrough,
    Image,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Style {
    pub effects: EnumSet<Effect>,
}

impl Default for Style {
    fn default() -> Self {
        Self::none()
    }
}

impl Style {
    pub fn none() -> Self {
        Style {
            effects: EnumSet::new(),
        }
    }

    pub fn merge(styles: &[Style]) -> Self {
        styles.iter().collect()
    }
}

impl From<Effect> for Style {
    fn from(effect: Effect) -> Self {
        Style {
            effects: enum_set!(effect),
        }
    }
}

impl<'a> FromIterator<&'a Style> for Style {
    fn from_iter<I: IntoIterator<Item = &'a Style>>(iter: I) -> Style {
        let mut effects = EnumSet::new();

        for style in iter {
            effects.insert_all(style.effects);
        }

        Style { effects }
    }
}

impl<T: Into<Style>> FromIterator<T> for Style {
    fn from_iter<I: IntoIterator<Item = T>>(iter: I) -> Style {
        iter.into_iter().map(Into::into).collect()
    }
}

impl IntoPy<PyObject> for Style {
    fn into_py(self, py: Python) -> PyObject {
        let effects: Vec<&str> = self
            .effects
            .iter()
            .map(|e| match e {
                Effect::Bold => "bold",
                Effect::Italic => "italic",
                Effect::Reverse => "reverse",
                Effect::Underline => "underline",
                Effect::Strikethrough => "strikethrough",
                Effect::Image => "image",
            })
            .collect();
        effects.into_py(py)
    }
}

#[pyclass]
#[derive(Clone, Debug, Default)]
pub struct Element {
    #[pyo3(get)]
    text: String,
    #[pyo3(get)]
    style: Style,
    #[pyo3(get)]
    target: Option<String>,
    #[pyo3(get)]
    image_info: Option<Image>,
}

impl Element {
    pub fn new(
        text: String,
        style: Style,
        target: Option<String>,
        image_info: Option<Image>,
    ) -> Element {
        Element {
            text,
            style,
            target,
            image_info,
        }
    }
}

pub trait Converter<A> {
    fn get_style(&self, annotation: &A) -> Option<Style>;

    fn get_link<'a>(&self, annotation: &'a A) -> Option<&'a str>;
}

fn ceil(x: u32, y: u32) -> u32 {
    x.saturating_add(y.saturating_sub(1))
        .checked_div(y)
        .unwrap_or(0)
}

pub struct RichConverter;

impl Converter<RichAnnotation> for RichConverter {
    fn get_style(&self, annotation: &RichAnnotation) -> Option<Style> {
        match annotation {
            RichAnnotation::Default => None,
            RichAnnotation::Link(_) => Some(Effect::Underline.into()),
            RichAnnotation::Image(_) => Some(Effect::Image.into()),
            RichAnnotation::Emphasis => Some(Effect::Italic.into()),
            RichAnnotation::Strong => Some(Effect::Bold.into()),
            RichAnnotation::Strikeout => Some(Effect::Strikethrough.into()),
            RichAnnotation::Code => None,
            RichAnnotation::Preformat(_) => None,
            RichAnnotation::Header(_) => Some(Effect::Bold.into()),
        }
    }

    fn get_link<'a>(&self, annotation: &'a RichAnnotation) -> Option<&'a str> {
        match annotation {
            RichAnnotation::Link(url) | RichAnnotation::Image(url) => Some(url),
            _ => None,
        }
    }
}

#[derive(Copy, Clone)]
pub struct Decorator<'a> {
    pub root_dir: &'a Path,
    pub term_info: TermSize,
}

impl<'a> Decorator<'a> {
    pub fn new(root_dir: &'a Path, term_info: TermSize) -> Decorator {
        Decorator {
            root_dir,
            term_info,
        }
    }

    fn create_image_from_path(&self, url: &str) -> Option<Image> {
        let path = Path::new(url);
        let data = path.file_name().and_then(|fname| {
            let full_path = Path::new(self.root_dir).join(fname);
            if let Ok(dimensions) = image::image_dimensions(&full_path) {
                Some((dimensions, full_path))
            } else {
                None
            }
        });

        if let Some((dimensions, full_path)) = data {
            let (img_width_px, img_height_px) = dimensions;
            let rows = self.term_info.row as u32;
            let cols = self.term_info.col as u32;
            let y = self.term_info.y as u32;
            let x = self.term_info.x as u32;
            let img_height_rows = ceil(img_height_px * rows, y);

            let img_width_cols = ceil(img_width_px * cols, x);

            let img_width_cols_fit = std::cmp::min(img_width_cols, cols);
            let img_height_rows_fit = ceil(img_width_cols_fit * img_height_rows, img_width_cols);

            Some(Image {
                size: (img_width_cols_fit, img_height_rows_fit),
                path: full_path,
                id: "".into(),
            })
        } else {
            None
        }
    }

    fn get_image_dimensions(&self, src: &str) -> (u32, u32) {
        self.create_image_from_path(src)
            .map(|i| i.size)
            .unwrap_or((0, 0))
    }

    pub fn get_image_info(&self, annotation: &'a RichAnnotation) -> Option<Image> {
        if let RichAnnotation::Image(url) = annotation {
            self.create_image_from_path(url)
        } else {
            None
        }
    }
}

impl<'a> TextDecorator for Decorator<'a> {
    type Annotation = RichAnnotation;

    fn decorate_link_start(&mut self, url: &str) -> (String, Self::Annotation) {
        ("".to_string(), RichAnnotation::Link(url.to_string()))
    }

    fn decorate_link_end(&mut self) -> String {
        "".to_string()
    }

    fn decorate_em_start(&mut self) -> (String, Self::Annotation) {
        ("".to_string(), RichAnnotation::Emphasis)
    }

    fn decorate_em_end(&mut self) -> String {
        "".to_string()
    }

    fn decorate_strong_start(&mut self) -> (String, Self::Annotation) {
        ("".to_string(), RichAnnotation::Strong)
    }

    fn decorate_strong_end(&mut self) -> String {
        "".to_string()
    }

    fn decorate_strikeout_start(&mut self) -> (String, Self::Annotation) {
        ("".to_string(), RichAnnotation::Strikeout)
    }

    fn decorate_strikeout_end(&mut self) -> String {
        "".to_string()
    }

    fn quote_prefix(&mut self) -> String {
        "".to_string()
    }

    fn unordered_item_prefix(&mut self) -> String {
        "".to_string()
    }

    fn ordered_item_prefix(&mut self, _: i64) -> String {
        "".to_string()
    }

    fn decorate_code_start(&mut self) -> (String, Self::Annotation) {
        ("".to_string(), RichAnnotation::Code)
    }

    fn decorate_code_end(&mut self) -> String {
        "".to_string()
    }

    fn decorate_header_start(&mut self, level: usize) -> (String, Self::Annotation) {
        ("".to_string(), RichAnnotation::Header(level))
    }

    fn decorate_header_end(&mut self) -> String {
        "".to_string()
    }

    fn decorate_preformat_first(&mut self) -> Self::Annotation {
        RichAnnotation::Preformat(false)
    }

    fn decorate_preformat_cont(&mut self) -> Self::Annotation {
        RichAnnotation::Preformat(true)
    }

    fn decorate_image(&mut self, _title: &str, src: &str) -> (String, Self::Annotation) {
        let (width, height) = self.get_image_dimensions(src);
        let mut first_row = "S".to_string();
        first_row.push_str(&"I".repeat(width.saturating_sub(1) as usize));
        let mut row = "I".repeat(width as usize);
        let remaining_row = if height > 1 {
            let remaining_width = self.term_info.col as usize - width as usize;
            "N".repeat(remaining_width)
        } else {
            "".to_string()
        };
        first_row.push_str(&remaining_row);
        row.push_str(&remaining_row);
        first_row.push_str(&row.repeat(height.saturating_sub(1) as usize));
        (first_row, RichAnnotation::Image(src.to_string()))
    }

    fn finalise(self) -> Vec<TaggedLine<RichAnnotation>> {
        Vec::new()
    }

    fn make_subblock_decorator(&self) -> Self {
        Decorator::new(self.root_dir, self.term_info)
    }
}
