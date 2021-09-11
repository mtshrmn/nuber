use pyo3::prelude::*;
mod book;
mod image;
mod parser;
use crate::book::Book;
use crate::image::Image;

#[pymodule]
fn libnuber(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Book>()?;
    m.add_class::<Image>()?;
    Ok(())
}
