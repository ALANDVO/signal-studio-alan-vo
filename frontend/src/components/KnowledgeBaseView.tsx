import React, { useState, useEffect } from "react";
import { KnowledgeDocument, KnowledgeChunk } from "../types/api";
import { api } from "../api/client";

export const KnowledgeBaseView: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [docName, setDocName] = useState("");
  const [docContent, setDocContent] = useState("");
  const [strategy, setStrategy] = useState<string>("structured_markdown");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KnowledgeChunk[]>([]);
  const [status, setStatus] = useState("");

  const loadDocuments = async () => {
    try {
      const data = await api.listDocuments();
      setDocuments(data);
    } catch (err: unknown) {
      setStatus(`Failed to load documents: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docName.trim() || !docContent.trim()) return;

    try {
      const created = await api.ingestDocument(docName.trim(), docContent.trim(), strategy);
      setDocName("");
      setDocContent("");
      await loadDocuments();
      setStatus(`Ingested "${created.name}" using strategy '${strategy}' into ${created.chunk_count} chunks.`);
    } catch (err: unknown) {
      setStatus(`Ingestion failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      const res = await api.searchKnowledge(searchQuery.trim());
      setSearchResults(res.matches);
      setStatus(`Found ${res.matches.length} matching knowledge chunks.`);
    } catch (err: unknown) {
      setStatus(`Search failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="knowledge-container">
      {status && <div className="status-banner">{status}</div>}

      <div className="knowledge-grid">
        {/* Ingestion Panel */}
        <section className="card ingestion-card">
          <h3>Ingest Document (Issue #12619)</h3>
          <p className="description-text">
            Choose tailored extraction strategies: Fast Text for ad-hoc chat files, Structured Markdown for hierarchical docs, or Semantic Chunks with sliding window overlap.
          </p>
          <form onSubmit={handleIngest} className="ingest-form">
            <input
              type="text"
              placeholder="Document Name (e.g. Model Guide)"
              value={docName}
              onChange={(e) => setDocName(e.target.value)}
              required
            />

            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              <option value="fast_text">fast_text (Fast heuristic, paragraph-level)</option>
              <option value="structured_markdown">structured_markdown (Header-aware, preserves code)</option>
              <option value="semantic_chunks">semantic_chunks (Sliding window with sentence overlap)</option>
            </select>

            <textarea
              placeholder="Paste raw markdown or document text..."
              rows={8}
              value={docContent}
              onChange={(e) => setDocContent(e.target.value)}
              required
            />

            <button type="submit" className="btn-primary">Ingest & Chunk</button>
          </form>
        </section>

        {/* Search & Query Panel */}
        <section className="card search-card">
          <h3>Knowledge Search & Retrieval</h3>
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Search concepts, embeddings, keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="btn-secondary">Search</button>
          </form>

          <div className="results-list">
            {searchResults.map((ch) => (
              <div key={ch.id} className="chunk-card">
                <div className="chunk-header">
                  <span className="badge">{ch.heading || "Section"}</span>
                  <span className="score-tag">Score: {ch.score?.toFixed(3)}</span>
                  <span className="token-tag">~{ch.token_count} words</span>
                </div>
                <div className="chunk-text">{ch.text}</div>
              </div>
            ))}
            {searchResults.length === 0 && searchQuery && (
              <div className="empty-hint">No chunks found matching this query.</div>
            )}
          </div>
        </section>
      </div>

      {/* Document Registry Table */}
      <section className="card doc-table-card">
        <h3>Registered Knowledge Documents</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Document Name</th>
              <th>Extraction Strategy</th>
              <th>Chunks</th>
              <th>Content Hash</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td><strong>{d.name}</strong></td>
                <td><span className="badge">{d.strategy}</span></td>
                <td>{d.chunk_count}</td>
                <td><code>{d.content_hash.slice(0, 10)}...</code></td>
                <td>{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center">No documents ingested yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
};
