"""Распознавание речи (faster-whisper) для ботов: путь к аудио → текст в stdout.

Запускается отдельным процессом, чтобы сбой нативной библиотеки не ронял бота.
    python utils/stt/transcribe.py voice.ogg
Модель — WHISPER_MODEL (по умолчанию small), кэш — WHISPER_CACHE.
"""
import os
import sys
from pathlib import Path


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
    segments, _info = model.transcribe(path, language="ru", beam_size=1, vad_filter=True)
    print(" ".join(s.text.strip() for s in segments).strip())


if __name__ == "__main__":
    main(sys.argv[1])
