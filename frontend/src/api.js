const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
let authToken = localStorage.getItem("repomind_token");

export function setAuthToken(token) {
  authToken = token;
  if (token) localStorage.setItem("repomind_token", token);
  else localStorage.removeItem("repomind_token");
}

function requestHeaders(json = false) {
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  };
}

async function getErrorMessage(response, fallback) {
  try {
    const data = await response.json();

    if (Array.isArray(data.detail)) {
      const messages = data.detail
        .map((item) => item?.msg)
        .filter(Boolean);

      if (messages.length > 0) {
        return messages.join(" ");
      }
    }

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (typeof data.message === "string") {
      return data.message;
    }

    if (typeof data.msg === "string") {
      return data.msg;
    }

    if (typeof data.error === "string") {
      return data.error;
    }

    return fallback;
  } catch {
    return fallback;
  }
}

export async function getRepositories() {
  const response = await fetch(`${API_BASE_URL}/repositories`, {
    headers: requestHeaders(),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Failed to fetch repositories."),
    );
  }

  const data = await response.json();

  return data.repositories || [];
}

export async function indexRepository(repoUrl) {
  const response = await fetch(`${API_BASE_URL}/repositories/index`, {
    method: "POST",

    headers: requestHeaders(true),

    body: JSON.stringify({
      repo_url: repoUrl,
    }),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Failed to index repository."),
    );
  }

  return response.json();
}

export async function askRepository(repoUrl, question, conversation = [], chatId = null) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",

    headers: requestHeaders(true),

    body: JSON.stringify({
      repo_url: repoUrl,
      question,
      conversation,
      chat_id: chatId,
    }),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Failed to ask repository."),
    );
  }

  return response.json();
}

export async function getIndexJob(jobId) {
  const response = await fetch(`${API_BASE_URL}/repositories/index/${jobId}`, {
    headers: requestHeaders(),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Failed to fetch indexing status."),
    );
  }

  return response.json();
}

export async function createChat(repositoryId) {
  const response = await fetch(`${API_BASE_URL}/repositories/${repositoryId}/chats`, {
    method: "POST",
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error(await getErrorMessage(response, "Failed to create chat."));
  return response.json();
}

export async function getChats(repositoryId) {
  const response = await fetch(`${API_BASE_URL}/repositories/${repositoryId}/chats`, {
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error(await getErrorMessage(response, "Failed to load chats."));
  return response.json();
}

export async function getChat(chatId) {
  const response = await fetch(`${API_BASE_URL}/chats/${chatId}`, {
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error(await getErrorMessage(response, "Failed to load chat."));
  return response.json();
}

export async function getRepositoryFiles(repositoryId) {
  const response = await fetch(`${API_BASE_URL}/repositories/${repositoryId}/files`, {
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error(await getErrorMessage(response, "Failed to load repository files."));
  return response.json();
}

export async function authenticate(mode, email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/${mode}`, {
    method: "POST",
    headers: requestHeaders(true),
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Authentication failed."));
  }

  return response.json();
}
