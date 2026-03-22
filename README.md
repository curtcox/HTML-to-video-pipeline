# HTML-to-Video Pipeline

Converts HTML articles into YouTube-ready MP4 videos with word-for-word narration, synchronized captions, QR codes for every citation, and diagrams for key concepts.

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

Run each pipeline stage individually, view generated frames/QR codes/audio, watch the assembled video, and clear outputs — all from the browser.

## CLI

```bash
source venv/bin/activate
python pipeline.py https://example.com/article.html
```

Options: `--dry-run`, `--output-dir`, `--segments-json`, `--voice-id`, `--width`, `--height`.

## Pipeline Stages

1. **Parse** — fetch HTML, extract text segments and citation URLs
2. **QR Codes** — generate scannable QR codes for each citation
3. **Visuals** — generate title cards, section cards, text frames, and diagrams
4. **Audio** — text-to-speech for each segment
5. **Captions** — generate SRT subtitle file from audio timing
6. **Assemble** — combine frames + audio + captions into final MP4 via ffmpeg
