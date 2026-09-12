from tree_sitter_languages import get_parser
from ingestion.chunker import chunk_text  # naive fallback

LANGUAGE_MAP = {
    ".py": "python",
}

CHUNK_NODE_TYPES = {
    "python": ("function_definition", "class_definition"),
}


def get_language_for_path(path: str):
    for ext, lang in LANGUAGE_MAP.items():
        if path.endswith(ext):
            return lang
    return None


def get_class_docstring(class_node, content_bytes: str):
    """Best-effort: grab a short summary from the class docstring if present."""
    for child in class_node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "expression_statement":
                    for sub in stmt.children:
                        if sub.type == "string":
                            text = content_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                            text = text.strip().strip('"""').strip("'''").strip()
                            first_line = text.split("\n")[0].strip()
                            return first_line[:150]
                            
    return None


def ast_chunk_file(content: str, path: str):
    language = get_language_for_path(path)
    if language is None:
        return None

    parser = get_parser(language)
    content_bytes = content.encode("utf-8")
    tree = parser.parse(content_bytes)
    root = tree.root_node

    chunk_types = CHUNK_NODE_TYPES[language]
    chunks = []

    def make_chunk(node, class_name=None, class_docstring=None):
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        text = content_bytes[node.start_byte:node.end_byte].decode("utf-8")

        # Prepend class context if this is a method
        if class_name:
            header = f"# Class: {class_name}\n"
            if class_docstring:
                header += f"# Class docstring: {class_docstring}\n"
            text = header + text

        chunks.append({
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
            "content": text,
            "node_type": node.type,
        })

    def walk(node, class_name=None, class_docstring=None):
        if node.type == "class_definition":
            docstring = get_class_docstring(node, content_bytes)
            found_method = False
            # Look inside the class body for methods
            for child in node.children:
                if child.type == "block":
                    for stmt in child.children:
                        target = stmt
                        # unwrap decorators to get to the function_definition
                        if stmt.type == "decorated_definition":
                            for sub in stmt.children:
                                if sub.type == "function_definition":
                                    target = sub
                                    break
                        if target.type == "function_definition":
                            found_method = True
                            make_chunk(target, class_name=node.child_by_field_name("name").text.decode("utf-8"), class_docstring=docstring)
            if not found_method:
                # Class with no methods (e.g. just attributes) — keep the whole class as a chunk
                make_chunk(node)
            return  # don't recurse further into this class

        if node.type == "decorated_definition":
            # unwrap to the function_definition
            for child in node.children:
                if child.type == "function_definition":
                    make_chunk(child, class_name=class_name, class_docstring=class_docstring)
                    return
        if node.type == "function_definition":
            make_chunk(node, class_name=class_name, class_docstring=class_docstring)
            return  # don't recurse into nested functions for now

        for child in node.children:
            walk(child, class_name=class_name, class_docstring=class_docstring)

    walk(root)
    return chunks


def chunk_file(content: str, path: str):
    """
    Tries AST-aware chunking first. Falls back to naive line-based
    chunking if the language isn't supported.
    """
    ast_chunks = ast_chunk_file(content, path)
    if ast_chunks is not None:
        return ast_chunks
    return chunk_text(content, path)

def debug_print_tree(node, content_bytes, indent=0):
    """Prints the AST tree structure so we can see actual node types."""
    text_preview = content_bytes[node.start_byte:node.end_byte].decode("utf-8")[:40].replace("\n", "\\n")
    print("  " * indent + f"{node.type}: {text_preview!r}")
    for child in node.children:
        debug_print_tree(child, content_bytes, indent + 1)

if __name__ == "__main__":
    sample_code = '''
class Greeter:
    """A simple greeter class."""

    def __init__(self, name):
        self.name = name

    @staticmethod
    def greet(name):
        return f"Hello, {name}!"
'''

    chunks = ast_chunk_file(sample_code, "sample.py")
    for c in chunks:
        print(f"\n--- {c['node_type']} (lines {c['start_line']}-{c['end_line']}) ---")
        print(c["content"])