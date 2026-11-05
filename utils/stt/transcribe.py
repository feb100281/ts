"""Распознавание речи (faster-whisper) для ботов: путь к аудио → текст в stdout.

Запускается отдельным процессом, чтобы сбой нативной библиотеки не ронял бота.
    python utils/stt/transcribe.py voice.ogg
Модель — WHISPER_MODEL (по умолчанию small), кэш — WHISPER_CACHE.
"""
import os
import sys
from pathlib import Path


def load_audio(path: str):
    """Аудио → 16 кГц моно float32. Через ffmpeg, если он есть: PyAV в окружении может
    быть старее, чем нужно faster-whisper. Без ffmpeg — путь к файлу как есть."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        return path
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path,
                          "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def main(path: str) -> None:
    from faster_whisper import WhisperModel

    root = Path(__file__).resolve().parents[2]
    model = WhisperModel(
        os.getenv("WHISPER_MODEL", "small"),
        device="cpu",
        compute_type="int8",
        cpu_threads=int(os.getenv("WHISPER_THREADS", "4")),
        download_root=os.getenv("WHISPER_CACHE", str(root / "data" / "whisper")),
    )
    segments, _info = model.transcribe(load_audio(path), language="ru", beam_size=1,
                                       vad_filter=True)
    print(" ".join(s.text.strip() for s in segments).strip())


if __name__ == "__main__":
    main(sys.argv[1])
