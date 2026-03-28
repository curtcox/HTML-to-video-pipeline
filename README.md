# HTML-to-Video Pipeline

Converts HTML articles into narrated MP4 videos with synchronized captions, QR codes, and optional user-defined diagram overlays.

## Requirements

- Python 3.10–3.13
- ffmpeg
- macOS (for `say` TTS) or Linux

## Quick Start

```bash
git clone https://github.com/curtcox/HTML-to-video-pipeline.git
cd HTML-to-video-pipeline
./install.sh
source venv/bin/activate
cd webapp && ./run.sh
```

Then open http://localhost:8080.

## What `install.sh` Does

1. Checks Python version (3.10–3.13) and ffmpeg
2. Creates a virtual environment in `venv/`
3. Installs core dependencies (Pillow, BeautifulSoup, qrcode, requests)
4. Prompts to install optional TTS backends
5. Sets file permissions for the web app

## TTS Providers

The pipeline supports four text-to-speech backends, configured via the web UI or `config.py`:

| Provider | Install | Notes |
|---|---|---|
| `say` (default) | None | macOS built-in. Works out of the box. |
| `kokoro` | `pip install -r requirements-kokoro.txt` | Local neural TTS, 82M params. Needs `espeak-ng` and Python ≤3.13. |
| `piper` | `pip install -r requirements-piper.txt` | Local neural TTS. Auto-downloads voice models. |
| `elevenlabs` | `pip install -r requirements-elevenlabs.txt` | Cloud API. Set `ELEVENLABS_API_KEY` env var. |

## Web App

The web app uses [fsrouter](https://github.com/curtcox/fsrouter) — a filesystem-based HTTP router where each route is a file named after its HTTP method.

```
webapp/
  fsrouter.py       # HTTP server
  run.sh            # sets PIPELINE_ROOT, PYTHONPATH, launches server
  routes/
    GET             # HTML UI (served at /)
    api/
      stages/
        parse/POST, qr/POST, visuals/POST,
        audio/POST, captions/POST, assemble/POST
      outputs/
        GET, DELETE
        frames/GET, qr/GET, audio/GET, video/GET
```

Run each pipeline stage individually, view generated frames/QR codes/audio, watch the assembled videos, and clear outputs from the browser.

## CLI

```bash
source venv/bin/activate
python pipeline.py https://example.com/article.html
```

Diagram rules can be supplied as multiline text or a file:

```text
https://example.com/pictures/cats.png >> Let's talk about cats >> but enough about cats for now.
```

CLI options include:
- `--diagram-specs-file`
- `--diagram-specs-text`
- `--video-modes text,diagrams,combined`
- plus existing options: `--dry-run`, `--output-dir`, `--segments-json`, `--voice-id`, `--width`, `--height`

## Pipeline Stages

1. **Parse** — fetch HTML, extract text segments and citation URLs
2. **QR Codes** — generate scannable QR codes for citation URLs and diagram image URLs
3. **Visuals** — generate text-track frames and separate diagram-track overlay frames
4. **Audio** — text-to-speech for each segment
5. **Captions** — generate SRT subtitle file from audio timing
6. **Assemble** — render:
   - `video_text.mp4` (vertical scrolling text track)
   - `video_diagrams.mp4` (horizontal scrolling diagram track)
   - `video_combined.mp4` (diagram overlay on text track)
   - plus `video.mp4` as the default combined output
