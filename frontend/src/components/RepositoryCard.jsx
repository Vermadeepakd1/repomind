function RepositoryCard({
    repository,
    onOpen,
    onReindex,
    onDelete,
    reindexing,
    deleting,
    indexing,
}) {
    const busy = indexing || reindexing || deleting;

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
                    disabled={busy}
                >
                    Open Chat
                </button>

                <button
                    className="secondary-button"
                    onClick={() =>
                        onReindex(repository)
                    }
                    disabled={busy}
                >
                    {reindexing ? (
                        <><span className="button-spinner" aria-hidden="true" /> Reindexing...</>
                    ) : "Reindex"}
                </button>

                <button
                    className="secondary-button danger-button"
                    onClick={() =>
                        onDelete(repository)
                    }
                    disabled={busy}
                >
                    {deleting ? "Deleting..." : "Delete"}
                </button>

            </div>

        </div>
    );
}

export default RepositoryCard;
