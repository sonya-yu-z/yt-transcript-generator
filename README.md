# yt-transcript-generator

A local utility for converting YouTube videos into plain-text transcript files for downstream analysis, summarization, and coding-agent workflows.

The tool prefers existing YouTube captions when available and can fall back to local speech-to-text transcription when necessary.

It is designed as a lightweight preprocessing utility rather than a hosted service or commercial transcription platform.

---

## Overview

The intended workflow is:

```text
YouTube URL
    ↓
yt-transcript-generator
    ↓
existing captions, if available
    ↓
local speech-to-text fallback, if needed
    ↓
clean .txt transcript
    ↓
downstream analysis
```

Typical use cases include:

- preparing video transcripts for LLM analysis;
- extracting source material for research or note-taking;
- generating clean plain-text transcripts for local workflows;
- reducing the need to manually copy and clean YouTube captions;
- providing coding agents with deterministic transcript files for further processing.

---

## Features

- Accepts standard YouTube URLs and video IDs
- Retrieves existing YouTube caption tracks when available
- Distinguishes manually created captions from automatically generated captions
- Falls back to local MLX Whisper transcription when captions cannot be retrieved
- Cleans caption fragmentation into readable paragraphs
- Supports optional paragraph-level timestamps
- Writes UTF-8 `.txt` transcript files
- Writes companion `.json` metadata files
- Uses deterministic filenames based on the YouTube video ID
- Reuses existing transcripts unless regeneration is explicitly requested
- Emits machine-readable status information to stdout
- Performs transcription locally without requiring a cloud transcription API

---

## Installation

Clone the repository and create an isolated Python environment:

```bash
git clone https://github.com/sonya-yu-z/yt-transcript-generator.git
cd yt-transcript-generator

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
```

---

## Usage

Basic usage:

```bash
python ytx.py "https://www.youtube.com/watch?v=sdsxk3yatkA"
```

The generated transcript and metadata are written directly to the user's Downloads directory.

Example output:

```text
VIDEO_ID=sdsxk3yatkA
CAPTION_RETRIEVAL=RETRIEVED
STATUS=RETRIEVED
SOURCE=YOUTUBE_AUTO_CAPTIONS
LANGUAGE=en
TRANSCRIPT=/Users/<user>/Downloads/sdsxk3yatkA.txt
METADATA=/Users/<user>/Downloads/sdsxk3yatkA.json
```

---

## Command-Line Options

Include paragraph-level timestamps:

```bash
python ytx.py "<URL>" --timestamps
```

Regenerate a transcript even if one already exists:

```bash
python ytx.py "<URL>" --force
```

Disable local Whisper fallback:

```bash
python ytx.py "<URL>" --no-whisper
```

Prefer one or more caption languages:

```bash
python ytx.py "<URL>" -l en
```

Multiple preferred languages can be supplied:

```bash
python ytx.py "<URL>" -l en -l zh
```

Force a language for local Whisper transcription:

```bash
python ytx.py "<URL>" --whisper-language en
```

---

## Retrieval Strategy

The preferred path is:

```text
YouTube URL
    ↓
existing caption track
    ↓
RETRIEVED
    ↓
clean transcript
    ↓
.txt
```

If captions cannot be retrieved:

```text
YouTube URL
    ↓
YouTube captions
    ↓
NOT_RETRIEVED
    ↓
local MLX Whisper transcription
    ↓
clean transcript
    ↓
.txt
```

The program distinguishes among explicit operational states rather than silently treating failed retrieval as an empty result.

Examples include:

```text
RETRIEVED
NOT_RETRIEVED
SOURCE_UNAVAILABLE
TRANSCRIPTION_FAILED
```

A failure to retrieve captions does not imply that captions or transcript content do not exist.

---

## Output

Each successful run produces two files in `~/Downloads`.

### Transcript

```text
sdsxk3yatkA.txt
```

The transcript file contains cleaned plain text intended for downstream analysis.

Example:

```text
KA is a 49 year old man presenting to the emergency room with fever,
headache, and confusion.

Five years ago, KA wasn't feeling well...
```

### Metadata

```text
sdsxk3yatkA.json
```

The metadata sidecar records information such as:

```json
{
  "video_id": "sdsxk3yatkA",
  "title": "Example video",
  "retrieval_status": "RETRIEVED",
  "transcript_source": "YOUTUBE_AUTO_CAPTIONS",
  "language": "en",
  "youtube_auto_generated": true
}
```

Keeping metadata separate from the transcript allows the `.txt` file to remain optimized for downstream model consumption while preserving retrieval provenance.

---

## Agent Workflows

The command-line interface is designed to be usable by local coding agents.

A typical automated workflow is:

```text
1. Run:
   python ytx.py "<URL>"

2. Read the emitted TRANSCRIPT path.

3. Open the generated .txt file.

4. Perform the requested analysis, summarization, extraction, or transformation.
```

This separates deterministic retrieval and preprocessing from higher-cost reasoning tasks.

---

## Local Speech-to-Text Fallback

When YouTube captions cannot be retrieved, the tool can fall back to local transcription using MLX Whisper.

The current default model is:

```text
mlx-community/whisper-large-v3-turbo
```

This path is intended primarily for Apple Silicon systems.

Audio is downloaded temporarily, transcribed locally, and removed after processing.

No cloud transcription API is required.

---

## Project Structure

```text
yt-transcript-generator/
├── README.md
├── requirements.txt
├── ytx.py
└── .gitignore
```

Generated transcripts are written outside the repository to the user's Downloads directory.

---

## Current Scope

Implemented:

- [x] local Python CLI
- [x] isolated virtual environment support
- [x] YouTube URL and video-ID parsing
- [x] caption retrieval
- [x] caption cleanup and paragraphization
- [x] `.txt` transcript output
- [x] `.json` metadata sidecar
- [x] deterministic video-ID filenames
- [x] explicit retrieval-status reporting
- [x] local MLX Whisper fallback
- [x] optional timestamps
- [x] force-regeneration option
- [x] agent-oriented stdout

Not currently in scope:

- web application
- user accounts
- hosted transcript database
- cloud transcription service
- analytics
- built-in summarization
- built-in LLM inference

The project intentionally stops at retrieval and preprocessing.

---

## Design Philosophy

Deterministic retrieval and preprocessing should happen before expensive model reasoning whenever possible.

```text
retrieve cheaply
        ↓
normalize locally
        ↓
reason downstream
```

The transcript generator handles retrieval and preprocessing.

Downstream systems handle interpretation.

---

## Notes

This project uses `youtube-transcript-api` for caption retrieval.

That library relies on an undocumented YouTube interface, which may change without notice. Caption retrieval may therefore occasionally break until the upstream library is updated.

Generated transcripts are local outputs and are not distributed or committed by this repository.

Users are responsible for ensuring that their use of transcript content complies with applicable copyright, platform, and other legal requirements.

---
