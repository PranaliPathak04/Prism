const BASE_URL = "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export function startIndex(owner, repo, branch = "main") {
  return request("/index", {
    method: "POST",
    body: JSON.stringify({ owner, repo, branch }),
  });
}

export function getIndexStatus(jobId) {
  return request(`/index/${jobId}`);
}

export function askQuestion(question, repo) {
  return request("/ask", {
    method: "POST",
    body: JSON.stringify({ question, repo }),
  });
}