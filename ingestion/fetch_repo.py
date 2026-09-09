import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_repo_files(owner: str, repo: str, branch: str = "main"):
    """
    Fetch all files from a public GitHub repo using the Git Trees API.
    Returns a list of dicts: {path, content}
    """
    # Step A: Get the full file tree (recursive)
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(tree_url , headers=HEADERS)
    resp.raise_for_status()
    tree = resp.json()["tree"]

    # Step B: Filter to code-like files only (basic filter for now)
    code_extensions = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rs", ".c", ".cpp")
    code_files = [item for item in tree if item["type"] == "blob" and item["path"].endswith(code_extensions)]

    print(f"Found {len(code_files)} code files out of {len(tree)} total tree entries.")

    # Step C: Fetch content for each file (limit to first 5 for now, just to test)
    results = []
    for item in code_files:
        blob_url = item["url"]
        blob_resp = requests.get(blob_url, headers=HEADERS)
        blob_resp.raise_for_status()
        blob_data = blob_resp.json()
        content = base64.b64decode(blob_data["content"]).decode("utf-8", errors="ignore")
        results.append({"path": item["path"], "content": content})

    return results


if __name__ == "__main__":
    files = get_repo_files(owner="pallets", repo="flask", branch="main")
    for f in files:
        print(f"\n--- {f['path']} ({len(f['content'])} chars) ---")