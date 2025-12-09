import os
from werkzeug.utils import secure_filename
from flask import current_app
def ingest_files(files, db, LogEntry, upload_folder):
    files = [f for f in files if f and f.filename.strip()]
    if not files:
        return 0, ["No files provided."]

    successes = 0
    failed = []

    for file in files:
        fname = secure_filename(file.filename)
        path = os.path.join(upload_folder, fname)
        try:
            file.save(path)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.rstrip()
                    if line:
                        db.session.add(LogEntry(filename=fname, content=line))
            successes += 1
        except Exception as exc:
            current_app.logger.error(f"Failed to ingest '{fname}': {exc}")
            failed.append(f"{fname}: {exc}")

    try:
        db.session.commit()
    except Exception as exc:
        current_app.logger.error(f"Database commit failed: {exc}")
        db.session.rollback()
        failed.append(f"Commit failed: {exc}")
        return successes, failed

    return successes, failed