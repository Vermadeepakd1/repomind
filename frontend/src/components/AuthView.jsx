import { useState } from "react";
import BrandMark from "./BrandMark";

function AuthView({ onAuthenticated, onBack }) {
    const [mode, setMode] = useState("login");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();
        setError("");
        setLoading(true);
        try {
            await onAuthenticated(mode, email, password);
        } catch (requestError) {
            setError(requestError.message || "Authentication failed.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="container auth-container">
            <section className="card auth-card">
                <BrandMark />
                <p className="subtitle">Understand any codebase with AI.</p>
                <button type="button" className="auth-back-button" onClick={onBack}>← Back to home</button>
                <div className="auth-tabs">
                    <button type="button" className={mode === "login" ? "auth-tab active" : "auth-tab"} onClick={() => setMode("login")}>Login</button>
                    <button type="button" className={mode === "register" ? "auth-tab active" : "auth-tab"} onClick={() => setMode("register")}>Register</button>
                </div>
                <form className="auth-form" onSubmit={handleSubmit}>
                    <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></label>
                    <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>
                    {error && <div className="error" role="alert">{error}</div>}
                    <button className="primary-button" disabled={loading}>
                        {loading ? <><span className="button-spinner" aria-hidden="true" /> Please wait...</> : mode === "login" ? "Login" : "Create account"}
                    </button>
                </form>
            </section>
        </main>
    );
}

export default AuthView;
