extern crate deunicode;
use deunicode::deunicode_char;

pub struct Range {
    pub start: usize,
    pub end: usize,
}

pub struct Deunicode {
    deunicoded: String,
    offsets: Vec<usize>,
}

impl From<&str> for Deunicode {
    fn from(s: &str) -> Self {
        let deunicoded_chars = s.chars().map(|c| deunicode_char(c).unwrap_or(""));
        Self {
            deunicoded: deunicoded_chars.clone().collect::<String>(),
            offsets: deunicoded_chars.map(|c| c.len()).collect(),
        }
    }
}

impl Deunicode {
    // unicoded -> original
    fn convert_offset(&self, offset: usize) -> Option<usize> {
        let mut count = 0;
        self.offsets
            .iter()
            .enumerate()
            .find(|(_, &c)| {
                count += c;
                offset < count
            })
            .map(|(i, _)| i)
    }

    pub fn match_indices<F>(&self, f: F, text: &str) -> Vec<Range>
    where
        F: Fn(&str) -> String,
    {
        let filtered_deunicoded = f(self.deunicoded.as_str());
        let filtered_text = f(text);
        filtered_deunicoded
            .match_indices(&filtered_text)
            .map(|(idx, s)| {
                let start = self.convert_offset(idx);
                let end = self.convert_offset(idx + s.len());
                (start, end)
            })
            .filter(|(s, e)| s.is_some() && e.is_some())
            .map(|(s, e)| Range {
                start: s.unwrap(),
                end: e.unwrap(),
            })
            .collect()
    }
}
