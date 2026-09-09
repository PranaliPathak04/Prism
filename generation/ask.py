import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads .env file

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL_NAME = "openai/gpt-oss-120b"


def build_context(chunks: list) -> str:
    """Formats retrieved chunks into a context block for the prompt."""
    parts = []
    for c in chunks:
        payload = c.payload
        parts.append(
            f"File: {payload['path']} (lines {payload['start_line']}-{payload['end_line']})\n"
            f"{payload['content']}\n"
        )
    return "\n---\n".join(parts)


def ask_question(question: str, chunks: list) -> str:
    """Sends the question + retrieved code context to Groq's LLM and returns the answer."""
    context = build_context(chunks)

    system_prompt = (
        "You are a helpful assistant that answers questions about a codebase. "
        "Only use the provided code context to answer. If the context doesn't contain "
        "enough information, say so clearly instead of guessing. "
        "Always cite the file path and line numbers you used in your answer."
    )

    user_prompt = f"Code context:\n{context}\n\nQuestion: {question}"

    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    from retrieval.search import search_chunks

    question = "how is the flask app created"
    chunks = search_chunks(question, repo_name="pallets/flask")
    answer = ask_question(question, chunks)

    print(f"Question: {question}\n")
    print(f"Answer:\n{answer}")