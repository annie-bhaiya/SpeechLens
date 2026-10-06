import re
import requests
from pathlib import Path
from backend.speechlens.config import ROOT

FILES = ["First Inauguration of FDR - Fear Itself Excerpt.ogg", "JFK inaugural address.ogg",
         "Eisenhower farewell address.ogg", "Roosevelt Pearl Harbor.ogg", "Tear down this wall.ogv"]

if __name__ == "__main__":
    directory = ROOT / "data/provenance/source_pages"
    directory.mkdir(parents=True, exist_ok=True)
    for title in FILES:
        url = "https://commons.wikimedia.org/wiki/File:" + title.replace(" ", "_")
        response = requests.get(url, timeout=45, headers={"User-Agent": "SpeechLensResearch/0.1 (source provenance collection)"})
        print(title, response.status_code)
        if response.ok:
            (directory / (title + ".html")).write_text(response.text, encoding="utf-8")
            urls = re.findall(r'https://upload.wikimedia.org[^\s"<>]+\.(?:ogg|ogv)', response.text)
            print(list(dict.fromkeys(urls))[:3])
