import os
import sys
import math
import requests
import io
import csv
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

if __package__ is None:
    sys.path.append(os.path.dirname(__file__))
    from config import DevConfig
    from services.ingest import ingest_files
else:
    from .config import DevConfig
    from .services.ingest import ingest_files

db = SQLAlchemy()

def create_app():

    load_dotenv()

    app = Flask(__name__)

    env = os.getenv("FLASK_ENV", "development").lower()
    app.config["ENV"] = env
    if env == "development":
        app.config.from_object(DevConfig)

    os.makedirs(app.instance_path, exist_ok=True)
    upload_dir = os.path.join(app.instance_path, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir
    db_path = os.path.join(app.instance_path, app.config.get("DB_NAME", "app.db"))
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    app.config["GEMINI_MODEL"] = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    app.config["GEMINI_API_BASE"] = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")
    app.config["GEMINI_TIMEOUT"] = int(os.getenv("GEMINI_TIMEOUT", "15"))

    db.init_app(app)

    class LogEntry(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        filename = db.Column(db.String(255), nullable=False)
        content = db.Column(db.Text, nullable=False)


# DOWNLOAD ALL LOGS AS CSV (WARNING THIS SHIT IS PROBABLY A BAD IDEA)
    @app.route("/download", methods=["GET"])
    def download_logs():
        def generate():
            columns = [c.name for c in LogEntry.__table__.columns]
            sio = io.StringIO()
            writer = csv.writer(sio)

            writer.writerow(columns)
            yield sio.getvalue()
            sio.seek(0); sio.truncate(0)

            stmt = db.select(LogEntry).order_by(LogEntry.id)
            for row in db.session.execute(stmt).scalars():
                writer.writerow([getattr(row, col) if getattr(row, col) is not None else "" for col in columns])
                yield sio.getvalue()
                sio.seek(0); sio.truncate(0)

        return Response(
            stream_with_context(generate()),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs.csv"},
        )

    with app.app_context():
        db.create_all()


    # THIS IS WHERE FLASK DIRECTS TO THE HTML FILES

#INDEX PAGE
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")


#UPLOAD PAGE
    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "GET":
            return render_template("upload.html")

        files = request.files.getlist("files")
        successes, failed = ingest_files(files, db, LogEntry, app.config["UPLOAD_FOLDER"])

        if failed and successes:
            status = f"Uploaded {successes} file(s), {len(failed)} failed."
            return render_template("upload.html", success=status, errors=failed)
        elif failed and not successes:
            return render_template("upload.html", error="All uploads failed.", errors=failed)
        else:
            return render_template("upload.html", success=f"Uploaded {successes} file(s) successfully.")

#VIEW PAGE
    @app.route("/view", methods=["GET"])
    def list_logs():
        per_page = request.args.get("per_page", default=20, type=int)
        if per_page not in (10, 20):
            per_page = 20

        total_count = db.session.query(db.func.count(LogEntry.id)).scalar() or 0
        total_pages = max(1, math.ceil(total_count / per_page)) if per_page else 1

        page = request.args.get("page", default=1, type=int)
        page = max(1, min(page, total_pages)) if total_pages else 1

        def build_page_numbers(current_page: int, pages: int, window: int = 2):
            visible = set(
                range(
                    max(1, current_page - window),
                    min(pages, current_page + window) + 1,
                )
            )
            visible.update({1, pages})

            sorted_pages = sorted(visible)
            page_list = []
            prev = None
            for p in sorted_pages:
                if prev and p - prev > 1:
                    page_list.append(None)
                page_list.append(p)
                prev = p
            return page_list

        offset = (page - 1) * per_page
        stmt = (
            db.select(LogEntry)
            .order_by(LogEntry.id.desc())
            .limit(per_page)
            .offset(offset)
        )
        rows = db.session.execute(stmt).scalars().all()

        page_start = offset + 1 if total_count else 0
        page_end = min(offset + per_page, total_count)

        return render_template(
            "view.html",
            logs=rows,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_count=total_count,
            page_start=page_start,
            page_end=page_end,
            page_numbers=build_page_numbers(page, total_pages),
        )

#QUERY PAGE
    @app.route("/query", methods=["GET", "POST"])
    def run_query():
        results = []
        error = None
        if request.method == "POST":
            filename = request.form.get("filename", "").strip()
            contains = request.form.get("contains", "").strip()
            stmt = db.select(LogEntry)
            if filename:
                stmt = stmt.where(LogEntry.filename == filename)
            if contains:
                stmt = stmt.where(LogEntry.content.contains(contains))
            try:
                results = db.session.execute(stmt.order_by(LogEntry.id.desc())).scalars().all()
            except Exception as exc:
                error = str(exc)
        return render_template("query.html", results=results, error=error)

#PURGE OPTION (horrible idea but whatever)
    @app.post("/purge")
    def purge():
        try:
            db.session.query(LogEntry).delete()
            db.session.commit()
            with db.engine.begin() as conn:
                conn.execute(text("VACUUM"))
            return jsonify({"status": "ok", "message": "Purged `log_entry` and vacuumed."}), 200
        except Exception as exc:
            app.logger.error(f"Purge failed: {exc}")
            db.session.rollback()
            return jsonify({"status": "error", "message": str(exc)}), 400

# Google stealing more data because the entire world is jerking off for  AI now
    @app.route("/api/gemini_chat", methods=["POST"])
    def api_gemini_chat():
        payload = request.get_json(silent=True) or {}
        user_message = (payload.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Message is required."}), 400

        api_key = app.config.get("GEMINI_API_KEY", "")
        if not api_key:
            return jsonify({"error": "Gemini API key not configured."}), 400

        model = app.config.get("GEMINI_MODEL", "gemini-1.5-flash")
        timeout = app.config.get("GEMINI_TIMEOUT", 15)
        base_url = app.config.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com").rstrip("/")
        url = f"{base_url}/v1beta/models/{model}:generateContent"
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": user_message
                        }
                    ]
                }
            ]
        }

        try:
            resp = requests.post(
                url,
                params={"key": api_key},
                json=body,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = ""
            candidates = data.get("candidates") or []
            if candidates:
                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []
                if parts:
                    reply = parts[0].get("text", "")
            if not reply:
                reply = "No response text returned."
            return jsonify({"reply": reply})
        except requests.RequestException as exc:
            error_body = ""
            if exc.response is not None:
                try:
                    error_body = exc.response.text
                except Exception:
                    error_body = ""
            msg = f"Gemini request failed: {exc}"
            if error_body:
                msg = f"{msg} | Response: {error_body}"
            return jsonify({
                "error": msg,
                "hint": "Check GEMINI_API_KEY/GOOGLE_API_KEY, GEMINI_MODEL (default gemini-1.5-flash-latest), and that the Generative Language API is enabled for your key.",
            }), 502
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    host = os.getenv("HOST", "127.0.0.3")
    port_str = os.getenv("PORT", "42069")

    try:
        port = int(port_str)
        if not (0 < port < 65536):
            raise ValueError("port must be between 1 and 65535")
    except ValueError:
        port = 42069

    app.run(debug=app.config.get("DEBUG", False), host=host, port=port)
