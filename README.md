# yt-transcript-generator

YouTube transcripts for shoggoth preprocessing.

A small local utility for turning YouTube videos into plain-text transcript files that can be read directly by Codex, ChatGPT, Claude, or other local coding-agent workflows.

This is not intended to be a web service or commercial transcription product.

It is a local preprocessing appliance.

---

## Purpose

The intended workflow is:

```text
YouTube URL
    ↓
yt-transcript-generator
    ↓
transcripts/<video-id>.txt
    ↓
local AI agent reads transcript
    ↓
summarization / analysis / extraction / chewing
```

Example:

> "Shoggy, chew https://www.youtube.com/watch?v=..."

A coding agent with access to this repository can:

1. run the transcript generator with the supplied URL;
2. write the transcript into the repository's `transcripts/` directory;
3. open the generated `.txt` file;
4. preprocess or analyze it directly.

The purpose is to eliminate the manual workflow of:

1. opening YouTube;
2. finding or copying a transcript;
3. cleaning it;
4. pasting it into an AI conversation.

---

## Design Goals

### Local first

Transcript processing should happen locally whenever possible.

The normal path uses an existing YouTube caption track rather than retranscribing audio unnecessarily.

A future fallback may use local speech-to-text when captions are unavailable.

### Agent friendly

The program should work cleanly inside automated coding-agent workflows.

It should:

- accept a YouTube URL as a command-line argument;
- require no interactive input during normal operation;
- write output to a deterministic repository folder;
- produce plain UTF-8 `.txt` files;
- print the resulting file path;
- return a nonzero exit code when generation fails.

### Plain text output

The primary output format is `.txt`.

The transcript should contain spoken content with unnecessary caption fragmentation removed.

Metadata should remain minimal so downstream agents receive mostly transcript rather than wrapper material.

### Predictable storage

Generated transcripts live under:

```text
transcripts/
```

Example:

```text
yt-transcript-generator/
├── README.md
├── requirements.txt
├── ytx.py
├── .gitignore
└── transcripts/
    ├── .gitkeep
    ├── sdsxk3yatkA.txt
    └── another-video-id.txt
```

The `transcripts/` directory is intentionally inside the repository so coding agents operating on the repository can immediately access generated transcript files.

Generated transcripts should normally remain untracked by Git.

---

## Planned CLI

Basic usage:

```bash
python ytx.py "https://www.youtube.com/watch?v=sdsxk3yatkA"
```

Expected output:

```text
RETRIEVED
transcripts/sdsxk3yatkA.txt
```

The program should print the final transcript path so an agent can immediately open it.

Possible future convenience command:

```bash
ytx "https://www.youtube.com/watch?v=sdsxk3yatkA"
```

---

## Retrieval Strategy

The preferred order is:

```text
YouTube URL
    ↓
existing YouTube caption track
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
optional local speech-to-text fallback
    ↓
.txt
```

The program should distinguish:

```text
RETRIEVED
NOT_RETRIEVED
SOURCE_UNAVAILABLE
TRANSCRIPTION_FAILED
```

A failed retrieval should not silently produce an empty transcript.

---

## Output

The primary transcript output should be readable plain text:

```text
KA is a 49 year old man presenting to the emergency room with fever,
headache, and confusion...

Five years ago, KA wasn't feeling well...
```

The program may optionally retain lightweight metadata in a companion file later, but the default `.txt` should remain optimized for model preprocessing.

Possible future sidecar:

```text
transcripts/sdsxk3yatkA.json
```

containing:

```json
{
  "video_id": "sdsxk3yatkA",
  "source": "youtube_auto_captions",
  "language": "en",
  "retrieval_status": "RETRIEVED"
}
```

This keeps epistemic metadata separate from the text fed to the model.

---

## Intended Agent Workflow

When this repository is available to a coding agent, a request such as:

> "Chew https://www.youtube.com/watch?v=sdsxk3yatkA"

can be interpreted as:

```text
1. Run:
   python ytx.py "<URL>"

2. Capture the generated transcript path.

3. Read:
   transcripts/<video-id>.txt

4. Perform the requested preprocessing or analysis.

5. Use the transcript as the source material rather than relying on memory
   or trying to reconstruct the video from web search.
```

The transcript generator handles retrieval.

The agent handles reasoning.

---

## Current Scope

Initial version:

- [x] local Python project
- [x] isolated virtual environment
- [x] `youtube-transcript-api`
- [ ] URL → transcript
- [ ] clean caption fragmentation
- [ ] `.txt` output
- [ ] deterministic `transcripts/` directory
- [ ] useful exit codes
- [ ] agent-oriented stdout
- [ ] local speech-to-text fallback

Not currently in scope:

- web application
- user accounts
- cloud transcription
- commercial API
- hosted transcript database
- analytics
- summarization inside the transcript program

Summarization and analysis belong downstream with the shoggoth.

---

## Philosophy

Do not spend frontier-model tokens reconstructing information that can be retrieved deterministically first.

```text
retrieve cheaply
        ↓
store plainly
        ↓
reason expensively
```

Transcript generation is preprocessing infrastructure.

The shoggoth should chew the transcript, not fight YouTube's interface.
```

For `.gitignore`, add:

```gitignore
.venv/
__pycache__/
*.pyc
.DS_Store

# Generated transcript working data
transcripts/*.txt
transcripts/*.json

# Keep directory in repo
!transcripts/.gitkeep
```
