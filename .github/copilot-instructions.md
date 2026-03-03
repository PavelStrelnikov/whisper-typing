# Copilot instructions for whisper-typing

Purpose
- Help AI coding agents become productive quickly in this Windows-focused Python app that inserts transcribed speech into the active window.

Big picture (what to know first)
- Entry points: [main.py](main.py) (dev console), [whisper_typing.pyw](whisper_typing.pyw) (GUI without console).
- UI vs core separation: UI code lives in [ui/](ui/) (controller and Tk windows) and business logic lives in [core/](core/) (audio, STT, hotkeys, injection, history).
- Two STT modes: local (faster-whisper) implemented in [core/stt_local.py](core/stt_local.py) and cloud (OpenAI API) in [core/stt_cloud.py](core/stt_cloud.py).

Critical workflows & commands
- Dev run (recommended): `python main.py` (see [README.md](README.md)).
- Quick dev wrapper: use `run_console.bat` to keep a console for logs.
- Production GUI: `run.bat` or `whisper_typing.pyw`.
- Build .exe: `pyinstaller whisper_typing.spec` or run `build.bat` (requires `pyinstaller`).
- Setup: Python 3.10+, create a venv and `pip install -r requirements.txt` (GPU users: `requirements-cuda.txt`).

Project-specific conventions and patterns
- Windows-first: many scripts (.bat) and runtime paths assume Windows (APPDATA storage). Logs and settings are in `%APPDATA%\WhisperTyping\` (see README).
- Settings persistence: runtime settings and history are JSON files under APPDATA; change defaults in [config/settings.py](config/settings.py) and [config/constants.py](config/constants.py).
- Hotkeys & mouse triggers: look at [core/hotkey_manager.py](core/hotkey_manager.py) for how triggers are registered; change behavior there, not only UI.
- Text injection: `core/text_injector.py` performs platform-specific window text insertion — review for focus/permission issues when modifying.
- Audio flow: `core/audio_recorder.py` captures audio chunks which are passed to STT implementations; follow that pipeline if changing buffer sizes or timing.

Integration points & external dependencies
- Local STT: faster-whisper (models downloaded on first run) — large models are multi-GB. See [README.md](README.md) notes about model sizes and performance tradeoffs.
- Cloud STT: OpenAI API — key is stored in settings; network and billing constraints apply. See [core/stt_cloud.py](core/stt_cloud.py).
- Packaging: PyInstaller spec is [whisper_typing.spec](whisper_typing.spec) — tests and behavior can differ when frozen; pay attention to model download paths and APPDATA when bundled.

Editing tips & safe change examples
- To change a default hotkey: update defaults in [config/settings.py](config/settings.py) and test with `run_console.bat` to catch global hotkey permission issues.
- To add a new STT backend: implement the same interface as `stt_local.py`/`stt_cloud.py` and wire it via the STT provider selection in [ui/settings_window.py](ui/settings_window.py) and [config/settings.py](config/settings.py).
- To debug UI behavior: run `python main.py` or `run_console.bat` to view logging; UI code is in [ui/app.py](ui/app.py) and windows in [ui/*.py](ui/).

What to watch for (pitfalls)
- Global hotkeys can require elevated privileges depending on the environment — reproduce on Windows target environments.
- Model downloads: faster-whisper models can be large and slow to download; avoid CI runs that accidentally trigger large model downloads.
- When freezing with PyInstaller, ensure model files and dynamic dependencies are included; the spec already attempts this but validate on a clean Windows VM.

Quick checklist for PR reviewers
- Verify Windows behavior locally (use `run_console.bat`).
- Confirm hotkey registration still works when changing `core/hotkey_manager.py`.
- If STT changes touch model handling, ensure first-run downloads are not unintentionally triggered in CI.

If anything is unclear or you want this file to include more code examples (e.g., exact function signatures to implement a new STT backend), tell me which sections to expand and I will iterate.
