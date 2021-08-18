use pyo3::prelude::*;
mod book;
mod image;
mod parser;
use book::Book;

#[pymodule]
fn libnuber(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Book>()?;
    Ok(())
}
