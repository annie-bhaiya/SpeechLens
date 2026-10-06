from pathlib import Path
import subprocess
import math
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from .config import PIPELINE
from .utils import sha256_file

EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".m4a", ".mp4", ".webm"}

def ffmpeg_executable():
    import shutil
    import imageio_ffmpeg
    return shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()

def decode(path, output=None):
    path = Path(path)
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError("Supported formats: WAV, FLAC, OGG, MP3, M4A, MP4, WebM.")
    if path.stat().st_size > PIPELINE["max_upload_bytes"]:
        raise ValueError("Upload exceeds 100 MB.")
    try:
        info = sf.info(path)
        if info.duration > PIPELINE["max_duration_s"]:
            raise ValueError("Audio exceeds ten minutes.")
        y, sr = sf.read(path, dtype="float32", always_2d=True)
        channels = y.shape[1]
        y = y.mean(axis=1)
        if sr != 16000:
            divisor = math.gcd(sr, 16000)
            y = resample_poly(y, 16000 // divisor, sr // divisor).astype(np.float32)
    except (RuntimeError, sf.LibsndfileError):
        # Bounded decode, no shell, no network protocol inputs, preserved original file.
        process = subprocess.run([ffmpeg_executable(), "-v", "error", "-nostdin", "-protocol_whitelist", "file,pipe,crypto",
                                  "-i", str(path.resolve()), "-t", "601", "-ac", "1", "-ar", "16000",
                                  "-f", "f32le", "pipe:1"], capture_output=True, timeout=60)
        if process.returncode:
            raise ValueError("Audio could not be decoded.")
        y = np.frombuffer(process.stdout, dtype="<f4").copy()
        sr, channels = None, None
    duration = len(y) / 16000
    if duration < 1.0 or duration > PIPELINE["max_duration_s"]:
        raise ValueError("Audio must last between one second and ten minutes.")
    if not np.isfinite(y).all() or np.sqrt(np.mean(y * y)) < 1e-5:
        raise ValueError("Audio is empty, silent, or contains invalid samples.")
    metadata = {"original_sha256": sha256_file(path), "sample_rate_hz": 16000,
                "original_sample_rate_hz": sr, "original_channels": channels,
                "duration_s": duration, "downmix": "arithmetic channel mean; no gain normalization",
                "clipped_fraction": float(np.mean(np.abs(y) >= .999)),
                "peak": float(np.max(np.abs(y)))}
    if output:
        sf.write(output, y, 16000, subtype="FLOAT")
        metadata["canonical_sha256"] = sha256_file(output)
    return y, metadata
