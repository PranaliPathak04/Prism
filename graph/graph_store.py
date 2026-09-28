import sqlite3
import hashlib


DB_PATH = "symbol_graph.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
    return conn


def init_db():
    """Creates the edges table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS call_edges (
            repo TEXT NOT NULL,
            caller TEXT NOT NULL,
            callee TEXT NOT NULL,
            path TEXT NOT NULL
        )
    """)
    # Index to make lookups by caller/callee fast
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caller ON call_edges(repo, caller)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_callee ON call_edges(repo, callee)")
    conn.commit()
    conn.close()


def store_edges(edges: list, repo_name: str):
    """Stores a list of (caller, callee, path) tuples for a given repo."""
    conn = get_connection()
    conn.executemany(
        "INSERT INTO call_edges (repo, caller, callee, path) VALUES (?, ?, ?, ?)",
        [(repo_name, caller, callee, path) for caller, callee, path in edges]
    )
    conn.commit()
    conn.close()


def clear_repo_edges(repo_name: str):
    """Removes existing edges for a repo (useful before re-indexing)."""
    conn = get_connection()
    conn.execute("DELETE FROM call_edges WHERE repo = ?", (repo_name,))
    conn.commit()
    conn.close()


def get_callees(function_name: str, repo_name: str):
    """What does this function call?"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT callee, path FROM call_edges WHERE repo = ? AND caller = ?",
        (repo_name, function_name)
    ).fetchall()
    conn.close()
    return rows


def get_callers(function_name: str, repo_name: str):
    """What calls this function?"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT caller, path FROM call_edges WHERE repo = ? AND callee = ?",
        (repo_name, function_name)
    ).fetchall()
    conn.close()
    return rows

def hash_content(content: str) -> str:
    """Returns a SHA256 hash of the content.Simple content hash to detect changes in files. Used for generating unique IDs for chunks."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def init_file_hashes_table():
    """Creates the file_hashes table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            repo TEXT NOT NULL,
            path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            PRIMARY KEY (repo, path)
        )
    """)
    conn.commit()
    conn.close()

def get_stored_file_hashes(repo_name: str) -> dict:
    """Returns a dict of {path: content_hash} for all files in the repo."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT path, content_hash FROM file_hashes WHERE repo = ?",
        (repo_name,)
    ).fetchall()
    conn.close()
    return {path: content_hash for path, content_hash in rows}

def update_file_hashes(repo_name: str , path_hash_pairs: list):
    """Updates the file_hashes table with new hashes for a repo. path_hash_pairs is a list of (path, content_hash) tuples."""
    conn = get_connection()
    conn.executemany(
        "INSERT INTO file_hashes (repo, path, content_hash) VALUES (?, ?, ?)"
        " ON CONFLICT(repo, path) DO UPDATE SET content_hash=excluded.content_hash",
        [(repo_name, path, content_hash) for path, content_hash in path_hash_pairs]
    )
    conn.commit()
    conn.close()

def clear_file_edges(repo_name: str, file_path: str):
    """Removes edges associated with a specific file in a repo."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM call_edges WHERE repo = ? AND path = ?",
        (repo_name, file_path)
    )
    conn.commit()
    conn.close()

def remove_file_hashes(repo_name: str, paths):
    """Removes the hash entry for files that no longer exist in the repo."""
    conn = get_connection()
    conn.executemany(
        "DELETE FROM file_hashes WHERE repo = ? AND path = ?",
        [(repo_name, p) for p in paths]
    )
    conn.commit()
    conn.close()

def clear_all_file_hashes():
    conn = get_connection()
    conn.execute("DELETE FROM file_hashes")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    from graph.call_extractor import extract_calls

    init_db()
    clear_repo_edges("test_repo")

    sample_code = '''
def helper(x):
    return x * 2

def main():
    result = helper(5)
    print(result)
    obj.some_method()
'''
    edges = extract_calls(sample_code, "sample.py")
    store_edges(edges, repo_name="test_repo")

    print("Callees of 'main':", get_callees("main", "test_repo"))
    print("Callers of 'helper':", get_callers("helper", "test_repo"))