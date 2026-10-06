"""Pinned English CTC inference + supplied-text CTC Viterbi alignment.

No generator labels, propagated boundaries or filenames enter inference.
ASR edit matching gates absent/low-confidence words; it is not an intelligibility score.
"""
from difflib import SequenceMatcher
from pathlib import Path
import threading
import numpy as np
from .config import PIPELINE, ROOT
from .utils import write_json, object_hash

_model = None
_processor = None
_lock = threading.Lock()

def greedy_words(log_probs, times, processor):
    """Greedy CTC words with acoustic native-time anchors (not forced labels)."""
    ids=np.argmax(log_probs,axis=-1)
    blank=processor.tokenizer.pad_token_id
    previous=None
    words=[]
    letters=[]
    a,b=None,None
    for index,token_id in enumerate(ids):
        token_id=int(token_id)
        if token_id==previous:
            if token_id!=blank and letters:
                b=float(times[index]+.01)
            continue
        previous=token_id
        if token_id==blank:
            continue
        character=processor.tokenizer.convert_ids_to_tokens(token_id)
        if character=="|":
            if letters:
                words.append({"text":"".join(letters).lower(),"start_s":a,"end_s":b})
            letters,a,b=[],None,None
        elif len(character)==1:
            if a is None:
                a=max(0,float(times[index]-.01))
            letters.append(character)
            b=float(times[index]+.01)
    if letters:
        words.append({"text":"".join(letters).lower(),"start_s":a,"end_s":b})
    return words

def load_model():
    global _model, _processor
    if _model is None:
        with _lock:
            if _model is None:
                import torch
                from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
                torch.set_num_threads(2)
                kwargs = {"revision": PIPELINE["alignment_revision"], "cache_dir": str(ROOT / ".cache/models")}
                snapshot=ROOT/".cache/models"/"models--facebook--wav2vec2-base-960h"/"snapshots"/PIPELINE["alignment_revision"]
                kwargs["local_files_only"]=(snapshot/"model.safetensors").exists() and (snapshot/"vocab.json").exists()
                _processor = Wav2Vec2Processor.from_pretrained(PIPELINE["alignment_model"], **kwargs)
                _model = Wav2Vec2ForCTC.from_pretrained(PIPELINE["alignment_model"], **kwargs).eval()
    return _model, _processor

def emissions(y):
    import torch
    model, processor = load_model()
    chunks, times = [], []
    width = int(PIPELINE["alignment_chunk_s"] * 16000)
    # Overlap gives acoustic context at chunk boundaries; assign every emission its actual native time.
    context = 8000
    for start in range(0, len(y), width):
        stop = min(len(y), start + width)
        lo, hi = max(0, start - context), min(len(y), stop + context)
        audio = processor(y[lo:hi], sampling_rate=16000, return_tensors="pt").input_values
        with torch.inference_mode():
            logits = model(audio).logits[0].log_softmax(-1).cpu().numpy()
        t = lo / 16000 + (np.arange(len(logits)) * 320 + 200) / 16000
        keep = (t >= start / 16000) & (t < stop / 16000)
        chunks.append(logits[keep])
        times.append(t[keep])
    return np.concatenate(chunks), np.concatenate(times), processor

def ctc_path(log_probs, targets, blank=0):
    """Full CTC state graph with blanks and repeat constraints, bounded memory."""
    states = np.full(2 * len(targets) + 1, blank, dtype=np.int32)
    states[1::2] = targets
    T, S = len(log_probs), len(states)
    if T * S > 35_000_000:
        raise ValueError("Transcript/audio alignment exceeds bounded memory; split the recording into excerpts.")
    previous = np.full(S, -np.inf, dtype=np.float32)
    previous[0] = 0
    back = np.zeros((T, S), dtype=np.uint8)
    skip = np.zeros(S, bool)
    skip[2:] = (states[2:] != blank) & (states[2:] != states[:-2])
    for t in range(T):
        advance = np.r_[-np.inf, previous[:-1]]
        jump = np.r_[-np.inf, -np.inf, previous[:-2]]
        jump[~skip] = -np.inf
        choices = np.stack((previous, advance, jump))
        best = np.argmax(choices, axis=0)
        back[t] = best
        previous = choices[best, np.arange(S)] + log_probs[t, states]
    state = S - 1 if previous[-1] >= previous[-2] else S - 2
    if not np.isfinite(previous[state]):
        raise ValueError("Transcript cannot be aligned to this audio.")
    path = np.zeros(T, np.int32)
    for t in range(T - 1, -1, -1):
        path[t] = state
        state -= int(back[t, state])
    return path

def align(y, transcript, cache_key=None, cache_root=None):
    cache = Path(cache_root or ROOT / ".cache/alignments") / f"{cache_key}.json" if cache_key else None
    if cache and cache.exists():
        import json
        return json.loads(cache.read_text())
    lp, times, processor = emissions(y)
    tokenizer = processor.tokenizer
    canonical = transcript["canonical_text"].upper()
    targets = tokenizer(canonical, add_special_tokens=False).input_ids
    if tokenizer.unk_token_id in targets:
        raise ValueError("Transcript includes unsupported alignment tokens.")
    path = ctc_path(lp, targets, tokenizer.pad_token_id)
    greedy = processor.batch_decode([np.argmax(lp, axis=-1)])[0].lower().split()
    intended = transcript["canonical_text"].split()
    matching = set()
    matcher = SequenceMatcher(None, intended, greedy, autojunk=False)
    edits = []
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == "equal":
            matching.update(range(a, b))
        else:
            edits.append({"operation": tag, "intended_word_span": [a, b], "recognized_words": greedy[c:d]})
    words, cursor, normal_index = [], 0, 0
    duration = len(y) / 16000
    for token in transcript["tokens"]:
        count = len(token["normalized"])
        char_indices = np.arange(cursor, cursor + count)
        cursor += count + 1
        # English tokenizer maps each character, including the word separator, to one token.
        selected = np.isin(path, 2 * char_indices + 1)
        frames = np.flatnonzero(selected)
        scores = []
        for ch in char_indices:
            f = np.flatnonzero(path == 2 * ch + 1)
            if len(f):
                scores.extend(np.exp(lp[f, targets[ch]]).tolist())
        confidence = float(np.mean(scores)) if scores else 0.0
        normal_count = len(token["normalized"].split())
        recognized = all(i in matching for i in range(normal_index, normal_index + normal_count))
        normal_index += normal_count
        valid = len(frames) > 0 and confidence >= PIPELINE["min_word_confidence"] and (recognized or confidence >= .55)
        start = max(0.0, float(times[frames[0]] - .01)) if valid else None
        end = min(duration, float(times[frames[-1]] + .01)) if valid else None
        if start is not None and end - start > max(2.0, .25 * len(token["normalized"])):
            valid, start, end = False, None, None
        words.append({"id": token["id"], "text": token["text"], "start_s": start, "end_s": end,
                      "confidence": confidence, "recognized_match": recognized,
                      "source": "wav2vec2-ctc-supplied-text-v1", "review_status": "machine_unreviewed"})
    coverage = sum(w["start_s"] is not None for w in words) / len(words)
    result = {"words": words, "coverage": coverage, "recognized_text": " ".join(greedy), "edits": edits,
              "asr_match_fraction": len(matching) / max(1, len(intended)),
              "model": PIPELINE["alignment_model"], "revision": PIPELINE["alignment_revision"],
              "duration_s": duration, "independently_reviewed": False}
    if cache:
        write_json(cache, result)
    return result
