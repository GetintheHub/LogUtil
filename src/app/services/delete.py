import sqlite3
import sys
import shutil
from pathlib import Path

def purge_table(db_path: Path, table: str):
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table}")
        conn.commit()
        cur.execute("VACUUM")
        conn.commit()
        print(f"Purged all rows from table '{table}' and vacuumed the database.")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        sys.exit(1)
    finally:
        conn.close()

def delete_uploads(upload_dir: Path):
    if not upload_dir.exists():
        print(f"Uploads directory not found: {upload_dir}")
        return
    if not upload_dir.is_dir():
        print(f"Uploads path is not a directory: {upload_dir}")
        return

    deleted_count = 0
    for entry in upload_dir.iterdir():
        try:
            if entry.is_file() or entry.is_symlink():
                entry.unlink()
                deleted_count += 1
            elif entry.is_dir():
                shutil.rmtree(entry)
                deleted_count += 1
        except Exception as e:
            print(f"Failed to delete '{entry}': {e}")

    print(f"Deleted {deleted_count} item(s) from uploads directory '{upload_dir}'.")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent.parent
    project_root = base_dir.parent
    default_db = project_root / "src" / "app" / "instance" / "app.db"
    default_table = "log_entry"
    default_uploads = project_root / "src" / "app" / "instance" / "uploads"

    db_path = Path(sys.argv[1]).resolve() if len(sys.argv) >= 2 else default_db
    table = sys.argv[2] if len(sys.argv) >= 3 else default_table
    uploads_dir = Path(sys.argv[3]).resolve() if len(sys.argv) >= 4 else default_uploads

    print(f"Using database path: {db_path}")
    print(f"Database exists: {db_path.exists()}")
    purge_table(db_path, table)

    print(f"Using uploads directory: {uploads_dir}")
    print(f"Uploads directory exists: {uploads_dir.exists()}")
    print(f"Is directory: {uploads_dir.is_dir()}")
    delete_uploads(uploads_dir)