import re
from nltk.tokenize import RegexpTokenizer

_tokenizer = RegexpTokenizer(r"[A-Za-z]+|[\u0C00-\u0C7F]+|[\u0900-\u097F]+|[\u0B80-\u0BFF]+|[0-9]+")

def normalize_text(text):
    """Lightweight Unicode-preserving normalization; avoids destructive translation."""
    text = str(text or "").strip().lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^\w\s\u0C00-\u0C7F\u0900-\u097F\u0B80-\u0BFF]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text):
    return _tokenizer.tokenize(normalize_text(text))
