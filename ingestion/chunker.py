def chunk_text(text: str, path: str, max_lines: int = 60, overlap: int = 5):
    """
    Naive chunker: splits a file's content into overlapping blocks of lines.
    Returns a list of dicts: {path, start_line, end_line, content}
    """
    lines = text.splitlines()
    chunks = []

    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        chunk_lines = lines[start:end]
        chunk_content = "\n".join(chunk_lines)

        chunks.append({
            "path": path,
            "start_line": start + 1,   # 1-indexed for humans
            "end_line": end,
            "content": chunk_content
        })

        if end == len(lines):
            break
        start = end - overlap  # step forward, but overlap a bit for context continuity

    return chunks


if __name__ == "__main__":
    from ingestion.fetch_repo import get_repo_files

    files = get_repo_files(owner="pallets", repo="flask", branch="main")
    all_chunks = []
    for f in files:
        file_chunks = chunk_text(f["content"], f["path"])
        all_chunks.extend(file_chunks)

    print(f"Total chunks created: {len(all_chunks)}")
    for c in all_chunks[:3]:
        print(f"\n--- {c['path']} (lines {c['start_line']}-{c['end_line']}) ---")
        print(c["content"][:200], "...")