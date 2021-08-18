use pyo3::prelude::*;
use std::path::PathBuf;

#[pyclass]
#[derive(Clone, Debug)]
pub struct Image {
    #[pyo3(get)]
    pub size: (u32, u32),
    #[pyo3(get)]
    pub path: PathBuf,
    #[pyo3(get)]
    pub id: String,
}

impl Image {
    pub fn new(path: &str) -> Image {
        Image {
            size: (0, 0),
            path: PathBuf::from(path),
            id: "".into(),
        }
    }
}
