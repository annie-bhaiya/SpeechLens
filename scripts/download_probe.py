import requests
from backend.speechlens.config import ROOT

BASE="https://upload.wikimedia.org/wikipedia/commons/3/35/First_Inauguration_of_FDR_-_Fear_Itself_Excerpt.ogg"
if __name__=="__main__":
    for url in [BASE+"?download=1", BASE+"?speechlens=20261005", "https://commons.wikimedia.org/wiki/Special:Redirect/file/First_Inauguration_of_FDR_-_Fear_Itself_Excerpt.ogg", "https://upload.wikimedia.org/wikipedia/commons/transcoded/3/35/First_Inauguration_of_FDR_-_Fear_Itself_Excerpt.ogg/First_Inauguration_of_FDR_-_Fear_Itself_Excerpt.ogg.mp3"]:
        r=requests.get(url,timeout=30,headers={"User-Agent":"Mozilla/5.0 SpeechLens/0.1", "Referer":"https://commons.wikimedia.org/"})
        print(r.status_code,r.headers.get("Content-Type"),len(r.content),url,flush=True)
        if r.ok and ("audio" in r.headers.get("Content-Type","") or r.content.startswith(b'OggS')):
            path=ROOT/"data/originals"/("fdr_fear.mp3" if url.endswith("mp3") else "fdr_fear.ogg")
            path.write_bytes(r.content)
            break
        else:
            print(r.text[:400],flush=True)
