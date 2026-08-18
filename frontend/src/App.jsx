import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  getRepositories,
  indexRepository,
  askRepository,
} from "./api";

import RepositoryCard from "./components/RepositoryCard";


function App() {

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

  const [newRepoUrl, setNewRepoUrl] = useState("");
  const [indexing, setIndexing] = useState(false);


  // =========================
  // Chat state
  // =========================

  const [messages, setMessages] =
    useState([]);

  const [question, setQuestion] =
    useState("");

  const [asking, setAsking] =
    useState(false);


  // =========================
  // General state
  // =========================

  const [error, setError] =
    useState("");


  // =========================
  // Load repositories
  // =========================

  async function loadRepositories() {
    const data = await getRepositories();

    setRepositories(data);

    return data;
  }


  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getRepositories();

        if (cancelled) {
          return;
        }

        setRepositories(data);
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
  }, []);


  // =========================
  // Open repository chat
  // =========================

  function handleOpenRepository(
    repository
  ) {

    setError("");

    setSelectedRepository(
      repository
    );

    setMessages([]);

    setQuestion("");

  }


  // =========================
  // Back to repositories
  // =========================

  function handleBackToRepositories() {

    setSelectedRepository(
      null
    );

    setMessages([]);

    setQuestion("");

    setError("");

  }


  // =========================
  // Reindex repository
  // =========================

  async function handleReindex(
    repository
  ) {

    try {

      setError("");

      setReindexingId(
        repository.repository_id
      );

      const data =
        await indexRepository(
          repository.repo_url
        );


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

    } catch (err) {

      setError(
        err.message ||
        "Failed to reindex repository."
      );

    } finally {

      setReindexingId(null);

    }
  }

  async function handleIndexNewRepository() {

    if (!newRepoUrl.trim()) {
      setError(
        "Please enter a GitHub repository URL."
      );
      return;
    }

    try {

      setError("");
      setIndexing(true);

      await indexRepository(
        newRepoUrl.trim()
      );

      await loadRepositories();

      setNewRepoUrl("");

    } catch (err) {

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

    if (!question.trim()) {
      return;
    }

    if (!selectedRepository) {

      setError(
        "Please select a repository first."
      );

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


    setQuestion("");

    setError("");

    setAsking(true);


    try {

      const data =
        await askRepository(
          selectedRepository.repo_url,
          currentQuestion,
          conversation
        );


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

    } catch (err) {

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

  if (!selectedRepository) {

    return (

      <div className="app">

        <main className="container">

          <header className="header">

            <h1 className="logo">
              RepoMind
            </h1>

            <p className="subtitle">
              AI-powered repository understanding.
            </p>

          </header>
          <section className="card index-card">

            <h2 className="section-title">
              Index New Repository
            </h2>

            <p className="section-description">
              Connect a public GitHub repository and
              start asking questions about its code.
            </p>

            <div className="repo-form">

              <input
                type="text"
                className="repo-input"
                placeholder="https://github.com/user/repository"
                value={newRepoUrl}
                onChange={(event) =>
                  setNewRepoUrl(event.target.value)
                }
                disabled={indexing}
              />

              <button
                className="primary-button"
                onClick={handleIndexNewRepository}
                disabled={
                  indexing ||
                  !newRepoUrl.trim()
                }
              >
                {indexing
                  ? "Indexing..."
                  : "Index Repository"}
              </button>

            </div>

          </section>


          <section className="card">

            <h2 className="section-title">
              Indexed Repositories
            </h2>


            {repositoriesLoading && (

              <div className="loading">
                Loading repositories...
              </div>

            )}


            {!repositoriesLoading &&
              repositories.length === 0 && (

                <div className="empty-state">

                  <div className="empty-title">
                    No repositories indexed yet.
                  </div>

                  <div className="empty-description">
                    Index a GitHub repository to
                    start asking questions about
                    its code.
                  </div>

                </div>

              )}


            {!repositoriesLoading &&
              repositories.length > 0 && (

                <div className="repository-list">

                  {repositories.map(
                    (repository) => (

                      <RepositoryCard
                        key={
                          repository.repository_id
                        }

                        repository={
                          repository
                        }

                        onOpen={
                          handleOpenRepository
                        }

                        onReindex={
                          handleReindex
                        }

                        reindexing={
                          reindexingId ===
                          repository.repository_id
                        }
                      />

                    )
                  )}

                </div>

              )}

          </section>


          {error && (

            <div className="error">
              {error}
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


        {/* =========================
            Chat Header
        ========================= */}

        <header className="chat-header">

          <div>

            <button
              className="back-button"
              onClick={
                handleBackToRepositories
              }
            >
              ← Repositories
            </button>


            <h1 className="chat-repository-name">
              {
                selectedRepository.repo_name
              }
            </h1>


            <div className="chat-repository-url">

              {
                selectedRepository.repo_url
              }

            </div>


            <div className="chat-repository-meta">

              {
                selectedRepository.chunk_count
              }{" "}
              chunks

            </div>

          </div>


          <button
            className="secondary-button"
            onClick={() =>
              handleReindex(
                selectedRepository
              )
            }
            disabled={
              reindexingId ===
              selectedRepository.repository_id
            }
          >

            {reindexingId ===
              selectedRepository.repository_id
              ? "Reindexing..."
              : "Reindex"}

          </button>

        </header>


        {/* =========================
            Error
        ========================= */}

        {error && (

          <div className="error">
            {error}
          </div>

        )}


        {/* =========================
            Chat
        ========================= */}

        <section className="card chat-section">


          {/* Messages */}

          <div className="messages">


            {messages.length === 0 && (

              <div className="empty-chat">

                <div className="empty-chat-title">
                  Ask anything about this repository.
                </div>

                <div className="empty-chat-description">

                  For example:

                  <div className="example-question">
                    How is authentication implemented?
                  </div>

                  <div className="example-question">
                    Where is the database configured?
                  </div>

                  <div className="example-question">
                    How does the application start?
                  </div>

                </div>

              </div>

            )}


            {messages.map(
              (message, index) => (

                <div
                  key={index}
                  className={
                    message.role === "user"
                      ? "message message-user"
                      : "message message-assistant"
                  }
                >

                  <div className="message-role">

                    {message.role === "user"
                      ? "You"
                      : "RepoMind"}

                  </div>


                  <div className="message-content">

                    {message.role ===
                      "assistant" ? (

                      <ReactMarkdown>
                        {
                          message.content
                        }
                      </ReactMarkdown>

                    ) : (

                      <p>
                        {
                          message.content
                        }
                      </p>

                    )}

                  </div>


                  {/* Sources */}

                  {message.role ===
                    "assistant" &&
                    message.sources &&
                    message.sources.length >
                    0 && (

                      <div className="sources">

                        <div className="sources-title">
                          Sources
                        </div>


                        {message.sources.map(
                          (
                            source,
                            sourceIndex
                          ) => (

                            <div
                              key={
                                sourceIndex
                              }
                              className="source"
                            >

                              <div className="source-file">

                                {
                                  source.file
                                }

                              </div>


                              <div className="source-meta">

                                Lines{" "}
                                {
                                  source.start_line
                                }
                                –
                                {
                                  source.end_line
                                }

                                {" • "}

                                Relevance:{" "}
                                {
                                  typeof source.score ===
                                    "number"
                                    ? source.score.toFixed(
                                      3
                                    )
                                    : "N/A"
                                }

                              </div>

                            </div>

                          )
                        )}

                      </div>

                    )}

                </div>

              )
            )}


            {/* Thinking indicator */}

            {asking && (

              <div className="message message-assistant">

                <div className="message-role">
                  RepoMind
                </div>

                <div className="loading">
                  Thinking...
                </div>

              </div>

            )}

          </div>


          {/* =========================
              Composer
          ========================= */}

          <div className="composer">

            <textarea
              className="question-input"
              placeholder="Ask anything about this repository..."
              value={question}
              onChange={(event) =>
                setQuestion(
                  event.target.value
                )
              }
              onKeyDown={
                handleQuestionKeyDown
              }
              disabled={asking}
              rows={2}
            />


            <button
              className="primary-button"
              onClick={handleAsk}
              disabled={
                asking ||
                !question.trim()
              }
            >

              {asking
                ? "Thinking..."
                : "Send"}

            </button>

          </div>


          <div className="composer-hint">
            Press Enter to send • Shift + Enter
            for a new line
          </div>

        </section>

      </main>

    </div>

  );
}


export default App;