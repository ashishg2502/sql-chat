import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [dbId, setDbId] = useState(null);
  const [schema, setSchema] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    setError("");
    setResult(null);

    try {
      const res = await fetch(`${API}/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) return setError(data.detail);
      setDbId(data.db_id);
      setSchema(data.schema);
    } catch {
      setError("Failed to connect to backend server.");
    } finally {
      setUploading(false);
    }
  }

  async function handleAsk() {
    if (!question) return;
    setLoading(true);
    setError("");
    setResult(null);

    const baseUrl = API || "http://localhost:8000";

    try {
      const res = await fetch(`${baseUrl}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ db_id: dbId, question }),
      });
      const data = await res.json();
      if (!res.ok) setError(data.detail);
      else setResult(data);
    } catch {
      setError("Network error connecting to backend API.");
    }
    setLoading(false);
  }

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", padding: 20, fontFamily: "sans-serif" }}>
      <h1>Ask Your Data (Text-to-SQL)</h1>
      <p>Upload a CSV file to begin querying in plain English.</p>

      {/* Upload Section */}
      <div style={{ padding: 16, border: "1px dashed #ccc", borderRadius: 8, marginBottom: 20 }}>
        <h3>1. Upload Dataset (.csv)</h3>
        <input type="file" accept=".csv" onChange={handleUpload} disabled={uploading} />
        {uploading && <p style={{ color: "#0070f3", marginTop: 8 }}>Uploading and parsing schema...</p>}
      </div>

      {/* Schema Display */}
      {schema && (
        <div style={{ marginBottom: 20 }}>
          <h3>Detected Schema</h3>
          <pre style={{ background: "#f4f4f4", padding: 12, borderRadius: 6, overflow: "auto" }}>
            {schema}
          </pre>
        </div>
      )}

      {/* Question Input */}
      {dbId && (
        <div style={{ marginBottom: 20 }}>
          <h3>2. Ask a Question</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              style={{ flex: 1, padding: 10, fontSize: 16, borderRadius: 4, border: "1px solid #ccc" }}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !loading && handleAsk()}
              placeholder="e.g. List top 5 departments by average salary"
              disabled={loading}
            />
            <button
              onClick={handleAsk}
              disabled={loading || !question}
              style={{ padding: "10px 20px", fontSize: 16, cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </div>
        </div>
      )}

      {/* 🚀 Visual Loading Feedback State */}
      {loading && (
        <div
          style={{
            padding: 16,
            marginBottom: 20,
            background: "#eef6ff",
            borderLeft: "4px solid #0070f3",
            borderRadius: 4,
            color: "#0051a8",
            fontWeight: "500",
          }}
        >
          🤖 Analyzing schema & generating SQL...
        </div>
      )}

      {/* Error Output */}
      {error && <p style={{ color: "crimson", fontWeight: "bold" }}>{error}</p>}

      {/* Results Section */}
      {result && (
        <div>
          <h3>Generated SQL Query (Attempts: {result.attempts})</h3>
          <pre style={{ background: "#1e1e1e", color: "#00ff66", padding: 12, borderRadius: 6, overflow: "auto" }}>
            {result.sql}
          </pre>

          <h3>Query Results</h3>
          <div style={{ overflowX: "auto" }}>
            <table border="1" cellPadding="8" style={{ borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr style={{ background: "#f4f4f4" }}>
                  {result.columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((val, j) => (
                      <td key={j}>{String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}