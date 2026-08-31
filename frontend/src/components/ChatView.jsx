import { useEffect, useRef } from "react";

import Message from "./Message";
import RepositoryExplorer from "./RepositoryExplorer";
import BrandMark from "./BrandMark";

function ChatView({
    selectedRepository,
    messages,
    chatLoading,
    creatingChat,
    question,
    asking,
    reindexing,
    error,
    status,
    onBack,
    onReindex,
    onQuestionChange,
    onQuestionKeyDown,
    onExampleQuestion,
    onAsk,
    onLogout,
    onNewChat,
}) {
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "end",
        });
    }, [messages, asking]);

    return (
        <>
            <header className="chat-header">
                <div>
                    <button className="back-button" onClick={onBack} disabled={asking || reindexing || chatLoading || creatingChat}>
                        ← Repositories
                    </button>

                    <div className="chat-brand"><BrandMark compact /><span>Repository workspace</span></div>
                    <h1 className="chat-repository-name">
                        {selectedRepository.repo_name}
                    </h1>

                    <div className="chat-repository-url">
                        {selectedRepository.repo_url}
                    </div>

                    <div className="chat-repository-meta">
                        {selectedRepository.chunk_count} chunks
                    </div>
                </div>

                <button
                    className="secondary-button"
                    onClick={onReindex}
                    disabled={reindexing || asking || chatLoading || creatingChat}
                >
                    {reindexing ? <><span className="button-spinner" aria-hidden="true" /> Reindexing...</> : "Reindex"}
                </button>
                <button className="auth-logout-button" onClick={onLogout} disabled={asking || reindexing || chatLoading || creatingChat}>
                    Log out
                </button>
                <button className="secondary-button" onClick={onNewChat} disabled={asking || reindexing || chatLoading || creatingChat}>
                    {creatingChat ? "Creating..." : "New chat"}
                </button>
            </header>

            <RepositoryExplorer repositoryId={selectedRepository.repository_id} />

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

            <section className="card chat-section">
                <div
                    className="messages"
                    aria-live="polite"
                    aria-busy={asking || chatLoading || creatingChat}
                >
                    {chatLoading && (
                        <div className="chat-loading-state" role="status">
                            <span className="loading-spinner" aria-hidden="true" />
                            <div>
                                <strong>Opening your workspace</strong>
                                <span>Loading the latest conversation...</span>
                            </div>
                        </div>
                    )}

                    {!chatLoading && messages.length === 0 && (
                        <div className="empty-chat">
                            <div className="empty-chat-title">
                                Ask anything about this repository.
                            </div>

                            <div className="empty-chat-description">
                                Try a developer workflow:

                                <button
                                    type="button"
                                    className="example-question"
                                    onClick={() => onExampleQuestion("How is authentication implemented?")}
                                    disabled={asking || chatLoading || creatingChat}
                                >
                                    How is authentication implemented?
                                </button>

                                <button
                                    type="button"
                                    className="example-question"
                                    onClick={() => onExampleQuestion("Where is the database configured?")}
                                    disabled={asking || chatLoading || creatingChat}
                                >
                                    Where is the database configured?
                                </button>

                                <button
                                    type="button"
                                    className="example-question"
                                    onClick={() => onExampleQuestion("How does the application start?")}
                                    disabled={asking || chatLoading || creatingChat}
                                >
                                    How does the application start?
                                </button>

                                <button
                                    type="button"
                                    className="example-question"
                                    onClick={() => onExampleQuestion("Explain the architecture of this repository.")}
                                    disabled={asking || reindexing || chatLoading || creatingChat}
                                >
                                    Explain the architecture of this repository.
                                </button>

                                <button
                                    type="button"
                                    className="example-question"
                                    onClick={() => onExampleQuestion("How do I run this project locally?")}
                                    disabled={asking || reindexing || chatLoading || creatingChat}
                                >
                                    How do I run this project locally?
                                </button>

                                <button
                                    type="button"
                                    className="example-question"
                                    onClick={() => onExampleQuestion("Where is authentication implemented and where are its main functions used?")}
                                    disabled={asking || reindexing || chatLoading || creatingChat}
                                >
                                    Find the authentication flow and its references.
                                </button>
                            </div>
                        </div>
                    )}

                    {messages.map((message, index) => (
                        <Message
                            key={index}
                            message={message}
                        />
                    ))}

                    {asking && (
                        <div className="message message-assistant">
                            <div className="message-role">
                                RepoMind
                            </div>

                            <div className="thinking" role="status">
                                <span className="thinking-label">Thinking about your question</span>
                                <span className="thinking-dots" aria-hidden="true">
                                    <span />
                                    <span />
                                    <span />
                                </span>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} aria-hidden="true" />
                </div>

                <div className="composer">
                    <textarea
                        className="question-input"
                        placeholder="Ask anything about this repository..."
                        value={question}
                        onChange={onQuestionChange}
                        onKeyDown={onQuestionKeyDown}
                        disabled={asking || reindexing || chatLoading || creatingChat}
                        aria-label="Question about the repository"
                        rows={2}
                    />

                    <button
                        className="primary-button"
                        onClick={onAsk}
                        disabled={asking || reindexing || chatLoading || creatingChat || !question.trim()}
                    >
                        {asking ? "Thinking…" : "Send"}
                    </button>
                </div>

                <div className="composer-hint">
                    Press Enter to send • Shift + Enter for a new line
                </div>
            </section>
        </>
    );
}

export default ChatView;
