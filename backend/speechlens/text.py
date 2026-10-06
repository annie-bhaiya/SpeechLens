import re
import unicodedata
from num2words import num2words
from .utils import object_hash

def canonicalize(text, language="en"):
    if language != "en":
        raise ValueError("Only English single-speaker speech is supported.")
    if not text or len(text) > 30000:
        raise ValueError("Supply a transcript between 1 and 30,000 characters.")
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    if re.search(r"[^\x00-\x7F]", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()) is not None:
        raise ValueError("Unsupported transcript characters.")
    tokens = []
    for match in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)*|\d+(?:\.\d+)?", text):
        display = match.group()
        normalized = num2words(display) if display[0].isdigit() else display.lower()
        normalized = re.sub(r"[^a-z' ]", " ", normalized.lower())
        tokens.append({"id": len(tokens), "text": display, "normalized": " ".join(normalized.split()),
                       "char_start": match.start(), "char_end": match.end()})
    if not tokens or len(tokens) > 2000:
        raise ValueError("Transcript must contain 1 to 2,000 English tokens.")
    canonical = " ".join(t["normalized"] for t in tokens)
    return {"display_text": text, "tokens": tokens, "canonical_text": canonical,
            "sha256": object_hash(canonical), "language": language}

def phrase_ids(transcript, max_words=12):
    groups, current = [], []
    for token in transcript["tokens"]:
        current.append(token["id"])
        after = transcript["display_text"][token["char_end"]:]
        if re.match(r"\s*[,;:.!?]", after) or len(current) >= max_words:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    # Very short clauses cannot support range/rate judgments: combine with a neighbour.
    merged = []
    for group in groups:
        if merged and (len(group) < 4 or len(merged[-1]) < 4):
            merged[-1].extend(group)
        else:
            merged.append(group)
    return merged
