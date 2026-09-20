#!/usr/bin/env python3

"""
yt-transcript-generator

Local YouTube transcript preprocessing for coding agents / shoggoths.

Preferred path:
    YouTube captions -> cleaned .txt

Fallback path:
    audio download -> local MLX Whisper -> cleaned .txt

Outputs:
    transcripts/<video_id>.txt
    transcripts/<video_id>.json

The .txt file is optimized for downstream model consumption.
The .json sidecar preserves retrieval/provenance metadata.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
TRANSCRIPT_DIR = Path.home() / "Downloads" / "YouTube Transcripts"

DEFAULT_LANGUAGES = ["en"]

# Good speed/quality tradeoff on Apple Silicon.
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

PARAGRAPH_TARGET_CHARS = 800
PARAGRAPH_MAX_GAP_SECONDS = 4.0


# ---------------------------------------------------------------------------
# Epistemic states
# ---------------------------------------------------------------------------

RETRIEVED = "RETRIEVED"
NOT_RETRIEVED = "NOT_RETRIEVED"
SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"


@dataclass
class TranscriptResult:
    video_id: str
    source: str
    retrieval_status: str
    text: str
    language: str | None = None
    is_generated: bool | None = None
    caption_error: str | None = None


# ---------------------------------------------------------------------------
# URL / identity handling
# ---------------------------------------------------------------------------

def extract_video_id(value: str) -> str:
    """
    Accept:
      - raw 11-character video ID
      - youtube.com/watch?v=...
      - youtu.be/...
      - youtube.com/shorts/...
      - youtube.com/embed/...
    """

    value = value.strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower()

    if hostname in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
        if candidate:
            return candidate

    youtube_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    }

    if hostname in youtube_hosts:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
            if candidate:
                return candidate

        for prefix in ("/shorts/", "/embed/", "/live/"):
            if parsed.path.startswith(prefix):
                parts = parsed.path.split("/")
                if len(parts) >= 3 and parts[2]:
                    return parts[2]

    raise ValueError(f"Could not extract a YouTube video ID from: {value}")


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


# ---------------------------------------------------------------------------
# Text cleanup
# ---------------------------------------------------------------------------

def format_timestamp(seconds: float) -> str:
    seconds = max(0, int(seconds))

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"


def clean_text(text: str) -> str:
    """
    Remove caption markup and normalize whitespace.
    """

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


@dataclass
class Segment:
    text: str
    start: float
    duration: float


def paragraphize(
    segments: Iterable[Segment],
    timestamps: bool = False,
) -> str:
    """
    Merge tiny caption/ASR segments into readable paragraphs.

    Break when:
      - accumulated text is sufficiently long, or
      - there is a noticeable pause between segments.
    """

    paragraphs: list[str] = []

    current_text: list[str] = []
    current_chars = 0
    paragraph_start: float | None = None
    previous_end: float | None = None

    def flush() -> None:
        nonlocal current_text
        nonlocal current_chars
        nonlocal paragraph_start

        if not current_text:
            return

        joined = " ".join(current_text).strip()

        if timestamps and paragraph_start is not None:
            joined = f"[{format_timestamp(paragraph_start)}] {joined}"

        paragraphs.append(joined)

        current_text = []
        current_chars = 0
        paragraph_start = None

    for segment in segments:
        text = clean_text(segment.text)

        if not text:
            continue

        start = float(segment.start)
        end = start + float(segment.duration)

        gap = None
        if previous_end is not None:
            gap = start - previous_end

        should_break = bool(
            current_text
            and (
                current_chars >= PARAGRAPH_TARGET_CHARS
                or (
                    gap is not None
                    and gap >= PARAGRAPH_MAX_GAP_SECONDS
                )
            )
        )

        if should_break:
            flush()

        if paragraph_start is None:
            paragraph_start = start

        current_text.append(text)
        current_chars += len(text) + 1
        previous_end = end

    flush()

    return "\n\n".join(paragraphs).strip()


# ---------------------------------------------------------------------------
# YouTube metadata
# ---------------------------------------------------------------------------

def get_video_title(url: str) -> str | None:
    """
    Fetch title using yt-dlp if available.

    Failure is nonfatal; video ID will be used instead.
    """

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "--quiet",
                "--no-warnings",
                "--print",
                "%(title)s",
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        title = result.stdout.strip()
        return title or None

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Caption retrieval
# ---------------------------------------------------------------------------

def fetch_youtube_transcript(
    video_id: str,
    languages: list[str],
    timestamps: bool,
) -> TranscriptResult:
    """
    Retrieve an existing YouTube transcript.

    youtube-transcript-api handles manual and automatically
    generated caption tracks.
    """

    api = YouTubeTranscriptApi()

    transcript = api.fetch(
        video_id,
        languages=languages,
    )

    segments = [
        Segment(
            text=item.text,
            start=float(item.start),
            duration=float(item.duration),
        )
        for item in transcript
    ]

    text = paragraphize(
        segments,
        timestamps=timestamps,
    )

    if not text:
        raise RuntimeError("YouTube returned an empty transcript.")

    source = (
        "YOUTUBE_AUTO_CAPTIONS"
        if transcript.is_generated
        else "YOUTUBE_MANUAL_CAPTIONS"
    )

    return TranscriptResult(
        video_id=video_id,
        source=source,
        retrieval_status=RETRIEVED,
        text=text,
        language=transcript.language_code,
        is_generated=transcript.is_generated,
    )


# ---------------------------------------------------------------------------
# Local Whisper fallback
# ---------------------------------------------------------------------------

def prepare_ffmpeg() -> Path:
    """
    imageio-ffmpeg ships/manages a usable ffmpeg binary.

    mlx-whisper normally expects an executable named 'ffmpeg'.
    We expose the imageio-managed binary through a temporary
    directory containing a symlink named exactly 'ffmpeg'.
    """

    import imageio_ffmpeg

    ffmpeg_binary = Path(imageio_ffmpeg.get_ffmpeg_exe())

    if not ffmpeg_binary.exists():
        raise RuntimeError(
            "imageio-ffmpeg could not provide an ffmpeg executable."
        )

    return ffmpeg_binary


def download_audio(
    url: str,
    destination: Path,
) -> Path:
    """
    Download best available audio without converting it.

    Avoiding conversion means yt-dlp itself does not require ffmpeg.
    """

    output_template = str(destination / "audio.%(ext)s")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--quiet",
            "--no-warnings",
            "-f",
            "bestaudio/best",
            "-o",
            output_template,
            url,
        ],
        check=True,
    )

    candidates = [
        path
        for path in destination.glob("audio.*")
        if path.is_file()
    ]

    if not candidates:
        raise RuntimeError(
            "yt-dlp completed but produced no audio file."
        )

    return candidates[0]


def whisper_transcribe(
    audio_path: Path,
    timestamps: bool,
    language: str | None,
) -> tuple[str, str | None]:
    """
    Transcribe audio completely locally using mlx-whisper.
    """

    import mlx_whisper

    ffmpeg_binary = prepare_ffmpeg()

    with tempfile.TemporaryDirectory(
        prefix="ytx-ffmpeg-"
    ) as ffmpeg_temp:

        shim_dir = Path(ffmpeg_temp)
        shim_path = shim_dir / "ffmpeg"

        try:
            shim_path.symlink_to(ffmpeg_binary)
        except FileExistsError:
            pass

        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{shim_dir}{os.pathsep}{old_path}"

        try:
            kwargs = {
                "path_or_hf_repo": WHISPER_MODEL,
                "verbose": False,
            }

            if language:
                kwargs["language"] = language

            result = mlx_whisper.transcribe(
                str(audio_path),
                **kwargs,
            )

        finally:
            os.environ["PATH"] = old_path

    raw_segments = result.get("segments") or []

    segments: list[Segment] = []

    for item in raw_segments:
        start = float(item.get("start", 0))
        end = float(item.get("end", start))

        segments.append(
            Segment(
                text=item.get("text", ""),
                start=start,
                duration=max(0.0, end - start),
            )
        )

    if segments:
        text = paragraphize(
            segments,
            timestamps=timestamps,
        )
    else:
        text = clean_text(result.get("text", ""))

    if not text:
        raise RuntimeError(
            "Local Whisper produced an empty transcript."
        )

    return text, result.get("language")


def fetch_with_whisper(
    video_id: str,
    timestamps: bool,
    language: str | None,
    caption_error: str,
) -> TranscriptResult:
    url = canonical_url(video_id)

    with tempfile.TemporaryDirectory(
        prefix=f"ytx-{video_id}-"
    ) as temp_directory:

        workdir = Path(temp_directory)

        audio_path = download_audio(
            url,
            workdir,
        )

        text, detected_language = whisper_transcribe(
            audio_path,
            timestamps=timestamps,
            language=language,
        )

    return TranscriptResult(
        video_id=video_id,
        source="LOCAL_MLX_WHISPER",
        retrieval_status=RETRIEVED,
        text=text,
        language=detected_language or language,
        is_generated=None,
        caption_error=caption_error,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_outputs(
    result: TranscriptResult,
    title: str,
    url: str,
    timestamps: bool,
) -> tuple[Path, Path]:

    TRANSCRIPT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    text_path = TRANSCRIPT_DIR / f"{result.video_id}.txt"
    metadata_path = TRANSCRIPT_DIR / f"{result.video_id}.json"

    text_path.write_text(
        result.text.strip() + "\n",
        encoding="utf-8",
    )

    metadata = {
        "video_id": result.video_id,
        "title": title,
        "url": url,
        "retrieval_status": result.retrieval_status,
        "transcript_source": result.source,
        "language": result.language,
        "youtube_auto_generated": result.is_generated,
        "timestamps_in_text": timestamps,
        "retrieved_at_utc": utc_now(),
        "caption_retrieval_error": result.caption_error,
        "whisper_model": (
            WHISPER_MODEL
            if result.source == "LOCAL_MLX_WHISPER"
            else None
        ),
        "text_file": str(text_path),
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return text_path, metadata_path


# ---------------------------------------------------------------------------
# Existing-output behavior
# ---------------------------------------------------------------------------

def existing_transcript(
    video_id: str,
) -> Path | None:

    path = TRANSCRIPT_DIR / f"{video_id}.txt"

    if path.exists() and path.stat().st_size > 0:
        return path

    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a local plaintext YouTube transcript "
            "for downstream agent preprocessing."
        )
    )

    parser.add_argument(
        "url",
        help="YouTube URL or raw video ID.",
    )

    parser.add_argument(
        "-l",
        "--language",
        action="append",
        dest="languages",
        help=(
            "Preferred YouTube caption language. "
            "Repeat for multiple languages. "
            "Default: en"
        ),
    )

    parser.add_argument(
        "-t",
        "--timestamps",
        action="store_true",
        help="Include paragraph-level timestamps.",
    )

    parser.add_argument(
        "--no-whisper",
        action="store_true",
        help=(
            "Do not fall back to local Whisper if "
            "YouTube captions cannot be retrieved."
        ),
    )

    parser.add_argument(
        "--whisper-language",
        default=None,
        help=(
            "Force Whisper language, e.g. en. "
            "Default: automatic detection."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate transcript even if one already exists.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_arguments()

    languages = args.languages or DEFAULT_LANGUAGES

    try:
        video_id = extract_video_id(args.url)

    except ValueError as exc:
        print(
            f"STATUS=INVALID_INPUT\nERROR={exc}",
            file=sys.stderr,
        )
        return 2

    url = canonical_url(video_id)

    if not args.force:
        existing = existing_transcript(video_id)

        if existing is not None:
            print("STATUS=ALREADY_EXISTS")
            print(f"VIDEO_ID={video_id}")
            print(f"TRANSCRIPT={existing}")
            return 0

    title = get_video_title(url) or video_id

    print(f"VIDEO_ID={video_id}")
    print(f"TITLE={title}")
    print("CAPTION_RETRIEVAL=ATTEMPTING")

    try:
        result = fetch_youtube_transcript(
            video_id=video_id,
            languages=languages,
            timestamps=args.timestamps,
        )

        print("CAPTION_RETRIEVAL=RETRIEVED")

    except Exception as caption_exception:

        caption_error = (
            f"{type(caption_exception).__name__}: "
            f"{caption_exception}"
        )

        print("CAPTION_RETRIEVAL=NOT_RETRIEVED")
        print(
            f"CAPTION_ERROR={caption_error}",
            file=sys.stderr,
        )

        if args.no_whisper:
            print("STATUS=NOT_RETRIEVED")
            return 3

        print("WHISPER_FALLBACK=ATTEMPTING")

        try:
            result = fetch_with_whisper(
                video_id=video_id,
                timestamps=args.timestamps,
                language=args.whisper_language,
                caption_error=caption_error,
            )

            print("WHISPER_FALLBACK=RETRIEVED")

        except Exception as whisper_exception:

            whisper_error = (
                f"{type(whisper_exception).__name__}: "
                f"{whisper_exception}"
            )

            print("STATUS=TRANSCRIPTION_FAILED")
            print(
                f"WHISPER_ERROR={whisper_error}",
                file=sys.stderr,
            )

            return 4

    text_path, metadata_path = write_outputs(
        result=result,
        title=title,
        url=url,
        timestamps=args.timestamps,
    )

    print("STATUS=RETRIEVED")
    print(f"SOURCE={result.source}")
    print(f"LANGUAGE={result.language or 'UNKNOWN'}")
    print(f"TRANSCRIPT={text_path}")
    print(f"METADATA={metadata_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())