import { useEffect, useState } from "react";

import { getRepositoryFiles } from "../api";

function RepositoryExplorer({ repositoryId }) {
    const [files, setFiles] = useState([]);
    const [search, setSearch] = useState("");
    const [expanded, setExpanded] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        let cancelled = false;
        queueMicrotask(() => {
            if (!cancelled) {
                setLoading(true);
                setError("");
            }
        });
        getRepositoryFiles(repositoryId)
            .then((data) => {
                if (!cancelled) setFiles(data.files || []);
            })
            .catch((requestError) => {
                if (!cancelled) setError(requestError.message || "Failed to load repository files.");
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [repositoryId]);

    const filteredFiles = files.filter((file) =>
        file.path.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <section className="repository-explorer card">
            <button type="button" className="explorer-toggle" onClick={() => setExpanded(!expanded)}>
                <span>Repository files</span>
                <span>{expanded ? "Hide" : `${files.length} files`}</span>
            </button>
            {expanded && (
                <div className="explorer-content">
                    <input className="explorer-search" placeholder="Search files..." value={search} onChange={(event) => setSearch(event.target.value)} />
                    {loading && (
                        <div className="explorer-loading" role="status">
                            <span className="loading-spinner" aria-hidden="true" />
                            Loading repository files...
                        </div>
                    )}
                    {error && <div className="source-error" role="alert">{error}</div>}
                    {!loading && !error && filteredFiles.map((file) => (
                        <div className="explorer-file" key={file.path}>
                            <span className="explorer-file-path">{file.path}</span>
                            <span className="explorer-file-meta">{file.line_count} lines</span>
                        </div>
                    ))}
                    {!loading && !error && filteredFiles.length === 0 && <div className="empty-description">No matching files.</div>}
                </div>
            )}
        </section>
    );
}

export default RepositoryExplorer;
