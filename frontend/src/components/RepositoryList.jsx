import RepositoryCard from "./RepositoryCard";

function RepositoryList({
    repositories,
    repositoriesLoading,
    reindexingId,
    indexing,
    onOpen,
    onReindex,
}) {
    if (repositoriesLoading) {
        return (
            <div className="repository-skeletons" role="status" aria-label="Loading repositories">
                {[1, 2, 3].map((item) => (
                    <div className="repository-skeleton" key={item}>
                        <span className="skeleton-line skeleton-title" />
                        <span className="skeleton-line skeleton-url" />
                        <span className="skeleton-line skeleton-meta" />
                        <span className="skeleton-button" />
                    </div>
                ))}
            </div>
        );
    }

    if (repositories.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-title">
                    No repositories indexed yet.
                </div>

                <div className="empty-description">
                    Index a GitHub repository to start asking
                    questions about its code.
                </div>
            </div>
        );
    }

    return (
        <div className="repository-list">
            {repositories.map((repository) => (
                <RepositoryCard
                    key={repository.repository_id}
                    repository={repository}
                    onOpen={onOpen}
                    onReindex={onReindex}
                    reindexing={
                        reindexingId === repository.repository_id
                    }
                    indexing={indexing}
                />
            ))}
        </div>
    );
}

export default RepositoryList;
