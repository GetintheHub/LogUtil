LogUtil
=======

LogUtil is a lightweight log storage and viewing utility implemented as a Flask app.
It accepts uploaded log files, stores them in a SQLite database, and provides a simple
web UI and API to view, download, and manage logs.

## FOR LINUX OPERATING SYSTEMS ONLY

## Requirements
- Python 3.8+
- `pip`
- Python packages (listed in `requirements.txt`):
  - `Flask 3.0.0`
  - `Werkzeug 3.0.0`
  - `SQLAlchemy 2.0.34`
  - `Flask-SQLAlchemy 3.1.1`
  - `python-dotenv 1.0.1`
  - `requests 2.31.0`
---

# Installation
```bash
git clone https://github.com/Trevor-M-Danielewski/LogUtil.git

cd LogUtil
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Run the App
```bash
python3 src/app/app.py
```
- The default host (`127.0.0.3`) and port (`42069`) — override via `HOST`/`PORT`.

## Project Structure
```plaintext
LogUtil/
├── `README.md`               # Project overview and setup instructions (this file)
├── `requirements.txt`        # Python dependencies for the project
├── `references.txt`          # Documentation references and links
├── `.env`                    # Environment variables and defaults (do not commit secrets)
├── `instance/`
│   ├── `app.db`              # SQLite database file (auto-generated at runtime)
│   └── `uploads/`            # Uploaded log files stored on disk
├── `src/`
│   └── `app/`
│       ├── `__init__.py`     # Package initializer (creates Flask app factory if used)
│       ├── `app.py`          # Main Flask app and route definitions (entry point)
│       ├── `config.py`       # Configuration classes and defaults (Dev/Prod)
│       ├── `services/`
│       │   ├── `ingest.py`   # File ingest helpers: parse, store, and index logs
│       │   └── `delete.py`   # File for deleting/purging logs from the DB
│       ├── `static/`
│       │   └── `css/`
│       │       ├── `base.css`  # Base CSS styles for the web UI
│       │       ├── `home.css`  # CSS style for the home page
│       │       ├── `query.css` # CSS styles for the query UI
│       │       ├── `upload.css`# CSS styles for the upload page
│       │       └── `view.css`  # CSS styles for the view page
│       └── `templates/`
│           ├── `index.html`   # Landing page template
│           ├── `upload.html`   # File upload form/template
│           ├── `view.html`     # Paginated log viewing template
│           ├── `query.html`    # Search / query UI template
│           └── `nav.html`      # Navigation partial included by other templates
```

Configuration
- Uses `.env` if present. Environment variables read by the app:
    - `FLASK_ENV` (defaults to `development`)
    - `GEMINI_API_KEY` or `GOOGLE_API_KEY` (required for `/api/gemini_chat`)
    - `GEMINI_MODEL` (default from code: `gemini-flash-latest` or similar)
    - `GEMINI_API_BASE` (default: `https://generativelanguage.googleapis.com`)
    - `GEMINI_TIMEOUT` (seconds, default `15`)
    - `DB_NAME` (optional - filename for the SQLite DB; default `app.db`)
    - `HOST` (app run host default `127.0.0.3`)
    - `PORT` (app run port default `42069`)
- Instance files:
    - Uploads stored at `instance/uploads`
    - DB stored at `instance/<DB_NAME>` (e.g., `instance/app.db`)

Usage
- Open the web UI at `http://<HOST>:<PORT>/` (defaults above).
- Use `/upload` to add log files (the ingest logic is in `services.ingest`).
- Use `/view` to browse logs with pagination.
- Use `/download` to stream all logs as a CSV (may be large).
- Use `/purge` (POST) to delete all logs and vacuum the DB — destructive action.

Security & Notes
- `/download` and `/purge` can expose or destroy all data; protect or disable in public deployments.
- The app proxies requests to an external Gemini API and requires a valid API key; do not commit keys to source control.
- The default host (`127.0.0.3`) and port (`42069`) — override via `HOST`/`PORT`.