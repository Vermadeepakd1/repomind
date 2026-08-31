import ReactMarkdown from "react-markdown";

function Message({ message }) {
    const isUser = message.role === "user";

    return (
        <div
            className={
                isUser
                    ? "message message-user"
                    : "message message-assistant"
            }
        >
            <div className="message-role">
                {isUser ? "You" : "RepoMind"}
            </div>

            <div className="message-content">
                {isUser ? (
                    <p>{message.content}</p>
                ) : (
                    <ReactMarkdown>
                        {message.content}
                    </ReactMarkdown>
                )}
            </div>

            {!isUser &&
                message.sources &&
                message.sources.length > 0 && (
                    <div className="sources">
                        <div className="sources-title">
                            Sources
                        </div>

                        {message.sources.map(
                            (source, sourceIndex) => (
                                <div
                                    key={sourceIndex}
                                    className="source"
                                >
                                    <div className="source-file">
                                        {source.file}
                                    </div>

                                    <div className="source-meta">
                                        Lines{" "}
                                        {source.start_line}
                                        –
                                        {source.end_line}

                                        {" • "}

                                        Relevance:{" "}
                                        {typeof source.score === "number"
                                            ? source.score.toFixed(3)
                                            : "N/A"}
                                    </div>

                                </div>
                            )
                        )}

                    </div>
                )}
        </div>
    );
}

export default Message;
