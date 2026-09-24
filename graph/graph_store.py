import sqlite3

DB_PATH = "symbol_graph.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
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