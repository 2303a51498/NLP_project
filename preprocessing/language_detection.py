def detect_language(text):
    """Heuristic script detector, not a certified language-identification model."""
    text = str(text or "")
    if any('\u0c00' <= c <= '\u0c7f' for c in text):
        return "Telugu script"
    if any('\u0900' <= c <= '\u097f' for c in text):
        return "Devanagari (Hindi or related)"
    if any('\u0b80' <= c <= '\u0bff' for c in text):
        return "Tamil script"
    if any(c.isalpha() for c in text):
        return "Latin script (English / Romanized text)"
    return "Unknown"
