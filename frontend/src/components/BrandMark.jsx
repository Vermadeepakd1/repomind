function BrandMark({ compact = false }) {
    return (
        <span className={compact ? "brand-mark brand-mark-compact" : "brand-mark"}>
            <img src="/logo.svg" alt="" aria-hidden="true" />
            {!compact && <span>RepoMind</span>}
        </span>
    );
}

export default BrandMark;
