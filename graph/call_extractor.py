from tree_sitter_languages import get_parser


def extract_calls(content: str, path: str):
    """
    Parses a Python file and extracts (caller_function, callee_name) pairs.
    A 'caller_function' is the name of the function containing the call.
    Calls made outside any function are attributed to caller '<module>'.
    """
    parser = get_parser("python")
    content_bytes = content.encode("utf-8")
    tree = parser.parse(content_bytes)
    root = tree.root_node

    edges = []  # list of (caller, callee, path)

    def get_call_name(call_node):
        """Extract the function name being called from a call_node."""
        func_part = call_node.child_by_field_name("function")
        if func_part is None:
            return None
        if func_part.type == "identifier":
            return content_bytes[func_part.start_byte:func_part.end_byte].decode("utf-8")
        if func_part.type == "attribute":
            # e.g. self.foo() or obj.method() -> just grab the last part "foo"/"method"
            attr = func_part.child_by_field_name("attribute")
            if attr:
                return content_bytes[attr.start_byte:attr.end_byte].decode("utf-8")
        return None

    def walk(node, current_function):
        if node.type in ("function_definition",):
            name_node = node.child_by_field_name("name")
            fn_name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
            for child in node.children:
                walk(child, current_function=fn_name)
            return

        if node.type == "call":
            callee = get_call_name(node)
            if callee:
                edges.append((current_function, callee, path))

        for child in node.children:
            walk(child, current_function=current_function)

    walk(root, current_function="<module>")
    return edges


if __name__ == "__main__":
    sample_code = '''
def helper(x):
    return x * 2

def main():
    result = helper(5)
    print(result)
    obj.some_method()
'''

    edges = extract_calls(sample_code, "sample.py")
    for caller, callee, path in edges:
        print(f"{caller} -> {callee}  ({path})")