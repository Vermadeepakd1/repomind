const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8200";
let authToken = localStorage.getItem("repomind_token");
let unauthorizedHandler = null;

export function setAuthToken(token) {
  authToken = token;
  if (token) localStorage.setItem("repomind_token", token);
  else localStorage.removeItem("repomind_token");
}

/**
 * Register a callback for when an authenticated request is rejected with 401
 * (for example, an expired token), so the app can sign the user out.
 */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
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

async function request(path, { method = "GET", body, signal, fallbackError }) {
  const sentWithToken = Boolean(authToken);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders(body !== undefined),
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!response.ok) {
    const message = await getErrorMessage(response, fallbackError);
    if (response.status === 401 && sentWithToken && unauthorizedHandler) {
      unauthorizedHandler(message);
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return response.status === 204 ? null : response.json();
}

export async function getRepositories() {
  const data = await request("/repositories", {
    fallbackError: "Failed to fetch repositories.",
  });
  return data.repositories || [];
}

export function indexRepository(repoUrl) {
  return request("/repositories/index", {
    method: "POST",
    body: { repo_url: repoUrl },
    fallbackError: "Failed to index repository.",
  });
}

export function deleteRepository(repositoryId) {
  return request(`/repositories/${repositoryId}`, {
    method: "DELETE",
    fallbackError: "Failed to delete repository.",
  });
}

export function askRepository(repoUrl, question, conversation = [], chatId = null) {
  return request("/ask", {
    method: "POST",
    body: {
      repo_url: repoUrl,
      question,
      conversation,
      chat_id: chatId,
    },
    fallbackError: "Failed to ask repository.",
  });
}

export function getIndexJob(jobId, { signal } = {}) {
  return request(`/repositories/index/${jobId}`, {
    signal,
    fallbackError: "Failed to fetch indexing status.",
  });
}

export function createChat(repositoryId) {
  return request(`/repositories/${repositoryId}/chats`, {
    method: "POST",
    fallbackError: "Failed to create chat.",
  });
}

export function getChats(repositoryId) {
  return request(`/repositories/${repositoryId}/chats`, {
    fallbackError: "Failed to load chats.",
  });
}

export function getChat(chatId) {
  return request(`/chats/${chatId}`, {
    fallbackError: "Failed to load chat.",
  });
}

export function deleteChat(chatId) {
  return request(`/chats/${chatId}`, {
    method: "DELETE",
    fallbackError: "Failed to delete chat.",
  });
}

export function getRepositoryFiles(repositoryId) {
  return request(`/repositories/${repositoryId}/files`, {
    fallbackError: "Failed to load repository files.",
  });
}

export function authenticate(mode, email, password) {
  return request(`/auth/${mode}`, {
    method: "POST",
    body: { email, password },
    fallbackError: "Authentication failed.",
  });
}
