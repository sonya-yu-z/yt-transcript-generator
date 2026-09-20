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
