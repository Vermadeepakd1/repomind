const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function indexRepository(repoUrl) {
  const response = await fetch(`${API_BASE_URL}/repositories/index`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repo_url: repoUrl,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to index repository");
  }

  return response.json();
}

export async function askRepository(repoUrl, question, conversation = []) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repo_url: repoUrl,
      question: question,
      conversation: conversation,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to ask repository");
  }

  return response.json();
}
