function RepositoryCard({
    repository,
    onOpen,
    onReindex,
    reindexing,
}) {
    return (
        <div className="repository-card">

            <div className="repository-card-main">

                <h3 className="repository-name">
                    {repository.repo_name}
                </h3>

                <p className="repository-url">
                    {repository.repo_url}
                </p>

                <div className="repository-meta">
                    <span>
                        {repository.chunk_count} chunks
                    </span>

                    <span>
                        Indexed{" "}
                        {new Date(
                            repository.indexed_at
                        ).toLocaleString()}
                    </span>
                </div>

            </div>

            <div className="repository-actions">

                <button
                    className="primary-button"
                    onClick={() =>
                        onOpen(repository)
                    }
                >
                    Open Chat
                </button>

                <button
                    className="secondary-button"
                    onClick={() =>
                        onReindex(repository)
                    }
                    disabled={reindexing}
                >
                    {reindexing
                        ? "Reindexing..."
                        : "Reindex"}
                </button>

            </div>

        </div>
    );
}

export default RepositoryCard;