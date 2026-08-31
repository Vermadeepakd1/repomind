import BrandMark from "./BrandMark";

function LandingPage({ onGetStarted, onLogin }) {
    return (
        <main className="landing-page">
            <nav className="landing-nav" aria-label="Main navigation">
                <BrandMark />
                <div className="landing-nav-actions">
                    <button className="landing-login-button" onClick={onLogin}>
                        Log in
                    </button>
                    <button className="primary-button landing-nav-cta" onClick={onGetStarted}>
                        Get started
                    </button>
                </div>
            </nav>

            <section className="landing-hero">
                <div className="landing-hero-copy">
                    <div className="landing-eyebrow">
                        <span className="eyebrow-dot" />
                        Your codebase, finally understandable
                    </div>
                    <h1>Ask your repository <span>anything.</span></h1>
                    <p>
                        RepoMind turns public GitHub repositories into a searchable,
                        conversational knowledge base. Find the right file, understand
                        the architecture, and move faster.
                    </p>
                    <div className="landing-hero-actions">
                        <button className="primary-button landing-main-cta" onClick={onGetStarted}>
                            Start exploring <span aria-hidden="true">→</span>
                        </button>
                        <span className="landing-note">Free to try · Public repositories</span>
                    </div>
                </div>

                <div className="landing-visual" aria-label="Example RepoMind conversation">
                    <div className="visual-glow" />
                    <div className="code-window">
                        <div className="window-bar">
                            <span /><span /><span />
                            <small>repomind / architecture</small>
                        </div>
                        <div className="code-line muted">01 <span>src/</span> &nbsp; <span>api/</span> &nbsp; <span>services/</span></div>
                        <div className="code-line active">02 <strong>How does authentication work?</strong></div>
                        <div className="answer-card">
                            <div className="answer-label"><BrandMark compact /> <span>Repository insight</span></div>
                            <p>Authentication starts in <code>auth.py</code>, where tokens are created and validated before requests reach the repository routes.</p>
                            <div className="answer-source"><span>●</span> app/auth.py <b>lines 12–48</b></div>
                        </div>
                        <div className="code-line muted">03 <span>Ready for your next question...</span></div>
                    </div>
                </div>
            </section>

            <section className="landing-features" aria-label="RepoMind features">
                <article className="landing-feature">
                    <div className="feature-icon">⌘</div>
                    <h2>Understand the whole picture</h2>
                    <p>Ask architecture-level questions and get answers grounded in your repository.</p>
                </article>
                <article className="landing-feature">
                    <div className="feature-icon">⌕</div>
                    <h2>Find what matters</h2>
                    <p>Jump from a question to the files and symbols that explain how the code works.</p>
                </article>
                <article className="landing-feature">
                    <div className="feature-icon">↗</div>
                    <h2>Move with confidence</h2>
                    <p>Spend less time searching and more time building, reviewing, and shipping.</p>
                </article>
            </section>

            <footer className="landing-footer">
                <BrandMark />
                <span>Clarity for every codebase.</span>
            </footer>
        </main>
    );
}

export default LandingPage;
