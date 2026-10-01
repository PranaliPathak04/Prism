TEST_CASES = [
    {
        "question": "what does the after_request decorator do",
        "repo": "pallets/flask",
        "expected_chunk_path": "src/flask/sansio/scaffold.py",
        "expected_answer": (
            "The after_request decorator registers a function to run after "
            "each request, storing it in after_request_funcs. Flask's "
            "process_response method later calls these registered functions "
            "in reverse order, passing them the response object so they can "
            "modify or replace it before it's sent to the client."
        ),
    },
    {
        "question": "how is the flask app created",
        "repo": "pallets/flask",
        "expected_chunk_path": "src/flask/sansio/app.py",
        "expected_answer": (
            "A Flask app is created by instantiating the Flask class, "
            "typically with the import name of the module or package, "
            "e.g. app = Flask(__name__)."
        ),
    },
    {
        "question": "what does before_request do",
        "repo": "pallets/flask",
        "expected_chunk_path": "src/flask/sansio/scaffold.py",
        "expected_answer": (
            "before_request registers a function to run before each request "
            "is handled. These functions run before the view function, and "
            "if one returns a value, that value is used as the response, "
            "skipping the view entirely."
        ),
    },
    {
        "question": "how does flask handle url routing",
        "repo": "pallets/flask",
        "expected_chunk_path": "src/flask/sansio/scaffold.py",
        "expected_answer": (
            "Flask handles routing through the add_url_rule method and the "
            "route decorator, which register a URL pattern and its handler "
            "function in the app's url_map, later used by Werkzeug's routing "
            "system to match incoming requests to the correct view."
        ),
    },
    {
        "question": "what does teardown_request do",
        "repo": "pallets/flask",
        "expected_chunk_path": "src/flask/sansio/scaffold.py",
        "expected_answer": (
            "teardown_request registers a function that runs after each "
            "request, even if an unhandled exception occurred. It's used "
            "for cleanup tasks like closing database connections, and "
            "unlike after_request, its return value is ignored."
        ),
    },
]