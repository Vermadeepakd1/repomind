import { useEffect, useRef, useState } from "react";

import {
  getRepositories,
  indexRepository,
  deleteRepository,
  getIndexJob,
  createChat,
  getChats,
  getChat,
  deleteChat,
  askRepository,
  authenticate,
  setAuthToken,
  setUnauthorizedHandler,
} from "./api";
import { pollIndexJob } from "./utils/pollIndexJob";

import RepositoryList from "./components/RepositoryList";
import ChatView from "./components/ChatView";
import AuthView from "./components/AuthView";
import BrandMark from "./components/BrandMark";
import LandingPage from "./components/LandingPage";
import { normalizeRepositoryUrl } from "./utils/repositoryUrl";


// Loads the most recent chat for a repository, creating one if none exist.
async function loadLatestChat(repositoryId) {
  const chatList = (await getChats(repositoryId)).chats || [];
  const latestChat = chatList[0];

  if (latestChat) {
    const chat = await getChat(latestChat.chat_id);
    return {
      chats: chatList,
      chatId: chat.chat_id,
      messages: chat.messages || [],
    };
  }

  const chat = await createChat(repositoryId);
  return { chats: [chat], chatId: chat.chat_id, messages: [] };
}

function App() {

  const [showAuth, setShowAuth] = useState(false);
  const [authNotice, setAuthNotice] = useState("");

  // Aborts in-flight indexing status polling (e.g. on logout).
  const pollingControllerRef = useRef(null);

  const [authToken, setAuthTokenState] = useState(
    () => localStorage.getItem("repomind_token")
  );

  // =========================
  // Repository state
  // =========================

  const [repositories, setRepositories] = useState([]);

  const [selectedRepository, setSelectedRepository] =
    useState(null);

  const [repositoriesLoading, setRepositoriesLoading] =
    useState(true);

  const [reindexingId, setReindexingId] =
    useState(null);

  const [deletingId, setDeletingId] =
    useState(null);

  const [newRepoUrl, setNewRepoUrl] = useState("");
  const [indexing, setIndexing] = useState(false);


  // =========================
  // Chat state
  // =========================

  const [messages, setMessages] =
    useState([]);

  const [chatId, setChatId] =
    useState(null);

  const [chats, setChats] =
    useState([]);

  const [chatLoading, setChatLoading] =
    useState(false);

  const [creatingChat, setCreatingChat] =
    useState(false);

  const [question, setQuestion] =
    useState("");

  const [asking, setAsking] =
    useState(false);


  // =========================
  // General state
  // =========================

  const [error, setError] =
    useState("");

  const [status, setStatus] =
    useState("");


  // =========================
  // Load repositories
  // =========================

  async function loadRepositories() {
    const data = await getRepositories();

    setRepositories(data);

    return data;
  }

  async function waitForIndexing(jobId) {
    const controller = new AbortController();
    pollingControllerRef.current = controller;

    try {
      return await pollIndexJob({
        jobId,
        fetchJob: getIndexJob,
        signal: controller.signal,
        onProgress: (job) =>
          setStatus(`Indexing: ${job.stage || "Working..."}`),
      });
    } finally {
      if (pollingControllerRef.current === controller) {
        pollingControllerRef.current = null;
      }
    }
  }

  function isAbortError(err) {
    return err?.name === "AbortError";
  }


  // Sign out automatically when the API rejects the stored token.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      handleLogout();
      setAuthNotice("Your session has expired. Please log in again.");
      setShowAuth(true);
    });

    return () => setUnauthorizedHandler(null);
  });


  useEffect(() => {
    if (!authToken) {
      return undefined;
    }

    let cancelled = false;

    async function load() {
      try {
        const data = await getRepositories();

        if (cancelled) {
          return;
        }

        setRepositories(data);

        const repositoryId = new URLSearchParams(window.location.search).get("repo");
        const repositoryFromUrl = data.find(
          (repository) => repository.repository_id === repositoryId
        );

        if (!cancelled && repositoryFromUrl) {
          handleOpenRepository(repositoryFromUrl);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }

        setError(
          err.message ||
          "Failed to load repositories."
        );
      } finally {
        if (!cancelled) {
          setRepositoriesLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [authToken]);


  async function handleAuthenticated(mode, email, password) {
    const data = await authenticate(mode, email, password);
    setAuthToken(data.token);
    setRepositoriesLoading(true);
    setAuthTokenState(data.token);
    setAuthNotice("");
    setShowAuth(false);
  }


  function handleLogout() {
    pollingControllerRef.current?.abort();
    pollingControllerRef.current = null;

    setAuthToken(null);
    setAuthTokenState(null);
    setAuthNotice("");
    setSelectedRepository(null);
    setRepositories([]);
    setMessages([]);
    setChats([]);
    setChatId(null);
    setQuestion("");
    setIndexing(false);
    setReindexingId(null);
    setError("");
    setStatus("");

    const url = new URL(window.location.href);
    url.searchParams.delete("repo");
    window.history.replaceState({}, "", url);
  }


  // =========================
  // Open repository chat
  // =========================

  async function handleOpenRepository(
    repository
  ) {

    setError("");
    setStatus("");

    setSelectedRepository(
      repository
    );

    const url = new URL(window.location.href);
    url.searchParams.set("repo", repository.repository_id);
    window.history.replaceState({}, "", url);

    setMessages([]);
    setChats([]);
    setChatId(null);
    setChatLoading(true);

    setQuestion("");

    try {
      const latest = await loadLatestChat(repository.repository_id);
      setChats(latest.chats);
      setChatId(latest.chatId);
      setMessages(latest.messages);
    } catch (err) {
      setError(err.message || "Failed to load chat history.");
    } finally {
      setChatLoading(false);
    }

  }


  async function openLatestChat(repositoryId) {
    const latest = await loadLatestChat(repositoryId);
    setChats(latest.chats);
    setChatId(latest.chatId);
    setMessages(latest.messages);
  }


  async function refreshChats(repositoryId) {
    try {
      const chatList = await getChats(repositoryId);
      setChats(chatList.chats || []);
    } catch {
      // The chat list is cosmetic here; the conversation itself is saved.
    }
  }


  async function handleSelectChat(nextChatId) {
    if (!nextChatId || nextChatId === chatId) return;

    try {
      setChatLoading(true);
      setError("");
      const chat = await getChat(nextChatId);
      setChatId(chat.chat_id);
      setMessages(chat.messages || []);
      setQuestion("");
    } catch (err) {
      setError(err.message || "Failed to load chat.");
    } finally {
      setChatLoading(false);
    }
  }


  async function handleDeleteChat() {
    if (!selectedRepository || !chatId) return;
    if (!window.confirm("Delete this chat and its messages? This cannot be undone.")) return;

    try {
      setChatLoading(true);
      setError("");
      await deleteChat(chatId);
      await openLatestChat(selectedRepository.repository_id);
      setQuestion("");
    } catch (err) {
      setError(err.message || "Failed to delete chat.");
    } finally {
      setChatLoading(false);
    }
  }


  // =========================
  // Back to repositories
  // =========================

  function handleBackToRepositories() {

    setSelectedRepository(
      null
    );

    const url = new URL(window.location.href);
    url.searchParams.delete("repo");
    window.history.replaceState({}, "", url);

    setMessages([]);
    setChats([]);
    setChatId(null);

    setQuestion("");

    setError("");
    setStatus("");

  }


  async function handleNewChat() {
    if (!selectedRepository) return;

    try {
      setCreatingChat(true);
      setError("");
      const chat = await createChat(selectedRepository.repository_id);
      setChats((previous) => [chat, ...previous]);
      setChatId(chat.chat_id);
      setMessages([]);
      setQuestion("");
      setError("");
    } catch (err) {
      setError(err.message || "Failed to create chat.");
    } finally {
      setCreatingChat(false);
    }
  }


  // =========================
  // Reindex repository
  // =========================

  async function handleReindex(
    repository
  ) {

    try {

      setError("");
      setStatus("");

      setReindexingId(
        repository.repository_id
      );
      setStatus("Preparing repository reindex...");

      const job = await indexRepository(repository.repo_url);
      const data = await waitForIndexing(job.job_id);


      // Refresh repository list
      await loadRepositories();


      // Update selected repository
      // if the user is currently chatting
      if (
        selectedRepository &&
        selectedRepository.repository_id ===
        repository.repository_id
      ) {

        setSelectedRepository(
          (current) => {

            if (!current) {
              return current;
            }

            return {
              ...current,
              chunk_count:
                data.chunk_count,
              indexed_at:
                new Date().toISOString(),
            };

          }
        );

      }

      setStatus(
        `${repository.repo_name} reindexed successfully with ${data.chunk_count} chunks.`
      );

    } catch (err) {

      if (isAbortError(err)) {
        return;
      }

      setError(
        err.message ||
        "Failed to reindex repository."
      );

    } finally {

      setReindexingId(null);

    }
  }


  async function handleDeleteRepository(repository) {
    if (
      !window.confirm(
        `Delete ${repository.repo_name}? Its index and all of its chats will be removed. This cannot be undone.`
      )
    ) {
      return;
    }

    try {
      setError("");
      setStatus("");
      setDeletingId(repository.repository_id);

      await deleteRepository(repository.repository_id);

      setRepositories((previous) =>
        previous.filter(
          (item) => item.repository_id !== repository.repository_id
        )
      );
      setStatus(`${repository.repo_name} was deleted.`);
    } catch (err) {
      setError(err.message || "Failed to delete repository.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleIndexNewRepository() {

    const trimmedUrl = newRepoUrl.trim();
    const normalizedUrl = normalizeRepositoryUrl(trimmedUrl);

    if (!trimmedUrl) {
      setStatus("");
      setError(
        "Please enter a GitHub repository URL."
      );
      return;
    }

    if (!normalizedUrl) {
      setStatus("");
      setError(
        "Enter a valid public GitHub repository URL, for example https://github.com/user/repository."
      );
      return;
    }

    if (
      repositories.some(
        (repository) => normalizeRepositoryUrl(repository.repo_url) === normalizedUrl
      )
    ) {
      setStatus("");
      setError(
        "This repository is already indexed. Use Reindex on its repository card to refresh it."
      );
      return;
    }

    try {

      setError("");
      setStatus("Preparing repository index...");
      setIndexing(true);

      const job = await indexRepository(trimmedUrl);
      await waitForIndexing(job.job_id);

      await loadRepositories();

      setNewRepoUrl("");
      setStatus("Repository indexed successfully.");

    } catch (err) {

      if (isAbortError(err)) {
        return;
      }

      setError(
        err.message ||
        "Failed to index repository."
      );

    } finally {

      setIndexing(false);

    }
  }

  // =========================
  // Ask repository
  // =========================

  async function handleAsk() {

    if (asking) {
      return;
    }

    if (!question.trim()) {
      return;
    }

    if (!selectedRepository) {

      setError(
        "Please select a repository first."
      );

      return;

    }

    if (!chatId) {
      setError("Chat history is still loading. Please try again in a moment.");
      return;
    }


    const currentQuestion =
      question.trim();


    // Build conversation for backend
    const conversation =
      messages.map(
        (message) => ({
          role: message.role,
          content: message.content,
        })
      );


    // Immediately show user's question
    setMessages(
      (previous) => [
        ...previous,
        {
          role: "user",
          content: currentQuestion,
        },
      ]
    );


    setError("");

    setAsking(true);


    try {

      const data =
        await askRepository(
          selectedRepository.repo_url,
          currentQuestion,
          conversation,
          chatId
        );


      if (!data.answer) {
        throw new Error(
          "The repository returned an empty answer."
        );
      }

      setQuestion("");

      setMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            content: data.answer,
            sources:
              data.sources || [],
          },
        ]
      );

      // The first question in a chat becomes its title on the server.
      refreshChats(selectedRepository.repository_id);

    } catch (err) {

      // Remove the optimistic user bubble on failure so a retry does not
      // duplicate it. The original text remains in the composer below.
      setMessages((previous) => {
        const lastMessage = previous[previous.length - 1];

        if (
          lastMessage?.role === "user" &&
          lastMessage.content === currentQuestion
        ) {
          return previous.slice(0, -1);
        }

        return previous;
      });

      // Keep the failed question in the composer so it can be edited or
      // submitted again instead of making the user reconstruct it.
      setQuestion(currentQuestion);

      setError(
        err.message ||
        "Failed to ask repository."
      );

    } finally {

      setAsking(false);

    }
  }


  // =========================
  // Enter key
  // =========================

  function handleQuestionKeyDown(
    event
  ) {

    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {

      event.preventDefault();

      handleAsk();

    }
  }


  // =========================
  // Repository List View
  // =========================

  if (!authToken) {
    if (!showAuth) {
      return (
        <LandingPage
          onGetStarted={() => setShowAuth(true)}
          onLogin={() => setShowAuth(true)}
        />
      );
    }

    return (
      <AuthView
        key={authNotice}
        notice={authNotice}
        onAuthenticated={handleAuthenticated}
        onBack={() => {
          setAuthNotice("");
          setShowAuth(false);
        }}
      />
    );
  }

  if (!selectedRepository) {

    return (

      <div className="app">

        <main className="container">

          <header className="workspace-topbar">
            <BrandMark />
            <div className="workspace-topbar-right">
              <span className="workspace-status"><span /> Workspace online</span>
              <button className="auth-logout-button" onClick={handleLogout}>Log out</button>
            </div>
          </header>

          <section className="workspace-intro">
            <div>
              <div className="workspace-kicker">REPOSITORY WORKSPACE</div>
              <h1>Your code, <em>in context.</em></h1>
              <p>Index a public repository and turn a sprawling codebase into a conversation you can actually follow.</p>
            </div>
            <div className="workspace-counter">
              <strong>{repositories.length.toString().padStart(2, "0")}</strong>
              <span>repositories<br />in your workspace</span>
            </div>
          </section>

          <section className="index-panel">
            <div className="index-panel-copy">
              <span className="panel-number">01</span>
              <div>
                <h2>Add a repository</h2>
                <p>Paste a public GitHub URL to create a searchable code map.</p>
              </div>
            </div>
            <div className="repo-form">
              <input type="text" className="repo-input" placeholder="github.com/owner/repository" value={newRepoUrl} onChange={(event) => setNewRepoUrl(event.target.value)} disabled={indexing} />
              <button className="primary-button" onClick={handleIndexNewRepository} disabled={indexing || !newRepoUrl.trim()}>
                {indexing ? <><span className="button-spinner" aria-hidden="true" /> Indexing...</> : "Index repository →"}
              </button>
            </div>
          </section>

          <section className="repository-section">
            <div className="section-heading-row">
              <div>
                <div className="workspace-kicker">YOUR LIBRARY</div>
                <h2>Indexed repositories</h2>
              </div>
              <span className="section-count">{repositories.length} total</span>
            </div>
            <RepositoryList
              repositories={repositories}
              repositoriesLoading={repositoriesLoading}
              reindexingId={reindexingId}
              deletingId={deletingId}
              indexing={indexing}
              onOpen={handleOpenRepository}
              onReindex={handleReindex}
              onDelete={handleDeleteRepository}
            />
          </section>


          {error && (

            <div className="error" role="alert">
              {error}
            </div>

          )}

          {status && (
            <div className="status" role="status">
              {status}
            </div>
          )}

        </main>

      </div>

    );
  }


  // =========================
  // Repository Chat View
  // =========================

  return (
    <div className="app">

      <main className="container">

        <ChatView
          selectedRepository={selectedRepository}
          messages={messages}
          chatLoading={chatLoading}
          creatingChat={creatingChat}
          question={question}
          asking={asking}
          reindexing={
            reindexingId ===
            selectedRepository.repository_id
          }
          error={error}
          status={status}
          onBack={handleBackToRepositories}
          onReindex={() =>
            handleReindex(selectedRepository)
          }
          onQuestionChange={(event) =>
            setQuestion(event.target.value)
          }
          onQuestionKeyDown={
            handleQuestionKeyDown
          }
          onExampleQuestion={(example) => setQuestion(example)}
          onAsk={handleAsk}
          onLogout={handleLogout}
          onNewChat={handleNewChat}
          chats={chats}
          chatId={chatId}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
        />

      </main>

    </div>
  );
}


export default App;
