from tree_sitter_languages import get_parser
from ingestion.chunker import chunk_text  # our old naive chunker


# Map file extensions to tree-sitter language names
LANGUAGE_MAP = {
    ".py": "python",
}

# Node types we consider "chunk-worthy" per language
CHUNK_NODE_TYPES = {
    "python": ("function_definition", "class_definition"),
}


def get_language_for_path(path: str):
    for ext, lang in LANGUAGE_MAP.items():
        if path.endswith(ext):
            return lang
    return None


def ast_chunk_file(content: str, path: str):
    """
    Parses a file with tree-sitter and extracts function/class-level chunks.
    Returns None if the language isn't supported (caller should fall back).
    """
    language = get_language_for_path(path)
    if language is None:
        return None

    parser = get_parser(language)
    tree = parser.parse(content.encode("utf-8"))
    root = tree.root_node

    chunk_types = CHUNK_NODE_TYPES[language]
    chunks = []

    def walk(node):
        if node.type in chunk_types:
            start_line = node.start_point[0] + 1  # tree-sitter is 0-indexed
            end_line = node.end_point[0] + 1
            text = content.encode("utf-8")[node.start_byte:node.end_byte].decode("utf-8")

            chunks.append({
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "content": text,
                "node_type": node.type,
            })
            # Don't recurse into children of a captured node —
            # we don't want a method inside a class captured separately AND as part of the class.
            return

        for child in node.children:
            walk(child)

    walk(root)
    return chunks

def chunk_file(content: str, path: str):
    """
    Tries AST-aware chunking first. Falls back to naive line-based
    chunking if the language isn't supported by our tree-sitter setup.
    """
    ast_chunks = ast_chunk_file(content, path)
    if ast_chunks is not None:
        return ast_chunks
    return chunk_text(content, path)


if __name__ == "__main__":
    sample_code = '''
import os

class Greeter:
    """A simple greeter class."""

    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"


def standalone_function(x, y):
    return x + y
'''

    chunks = ast_chunk_file(sample_code, "sample.py")
    for c in chunks:
        print(f"\n--- {c['node_type']} (lines {c['start_line']}-{c['end_line']}) ---")
        print(c["content"])