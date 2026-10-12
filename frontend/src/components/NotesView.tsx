import React, { useState, useEffect } from "react";
import { Note } from "../types/api";
import { api } from "../api/client";

export const NotesView: React.FC = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [activeNote, setActiveNote] = useState<Note | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [status, setStatus] = useState("");

  const loadNotes = async () => {
    try {
      const data = await api.listNotes(searchQuery);
      setNotes(data);
      if (data.length > 0 && !activeNote) {
        selectNote(data[0]);
      }
    } catch (err: unknown) {
      setStatus(`Failed to load notes: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const selectNote = (n: Note) => {
    setActiveNote(n);
    setTitle(n.title);
    setContent(n.content);
    setTags(n.tags);
  };

  useEffect(() => {
    loadNotes();
  }, [searchQuery]);

  const handleCreate = async () => {
    try {
      const created = await api.createNote("New Research Note", "Draft findings here...", "ai,research");
      await loadNotes();
      selectNote(created);
      setStatus("Created new note.");
    } catch (err: unknown) {
      setStatus(`Error creating note: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleSave = async () => {
    if (!activeNote) return;
    try {
      const updated = await api.updateNote(activeNote.id, title, content, tags);
      await loadNotes();
      selectNote(updated);
      setStatus("Note saved.");
    } catch (err: unknown) {
      setStatus(`Error saving note: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleDelete = async () => {
    if (!activeNote) return;
    try {
      await api.deleteNote(activeNote.id);
      setActiveNote(null);
      await loadNotes();
      setStatus("Note deleted.");
    } catch (err: unknown) {
      setStatus(`Error deleting note: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleExport = () => {
    if (!activeNote) return;
    const blob = new Blob([`# ${activeNote.title}\n\nTags: ${activeNote.tags}\n\n${activeNote.content}`], {
      type: "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeNote.title.replace(/\s+/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setStatus("Exported note as Markdown.");
  };

  return (
    <div className="notes-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h3>Notes Workspace</h3>
          <button className="btn-secondary" onClick={handleCreate}>+ New</button>
        </div>
        <input
          type="text"
          className="search-input"
          placeholder="Search notes or tags..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <ul className="chat-list">
          {notes.map((n) => (
            <li
              key={n.id}
              className={`chat-item ${activeNote?.id === n.id ? "active" : ""}`}
              onClick={() => selectNote(n)}
            >
              <div className="chat-item-title">{n.title}</div>
              <div className="chat-item-meta">{n.tags || "no tags"}</div>
            </li>
          ))}
        </ul>
      </aside>

      <main className="main-content">
        {status && <div className="status-banner">{status}</div>}

        {activeNote ? (
          <div className="note-editor">
            <div className="editor-toolbar">
              <input
                type="text"
                className="title-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Note title"
              />
              <div className="button-group">
                <button className="btn-secondary" onClick={handleExport}>Export .MD</button>
                <button className="btn-primary" onClick={handleSave}>Save</button>
                <button className="btn-danger" onClick={handleDelete}>Delete</button>
              </div>
            </div>

            <input
              type="text"
              className="tags-input"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Comma-separated tags (e.g. math, eval, prompt)"
            />

            <textarea
              className="content-textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Markdown content..."
            />
          </div>
        ) : (
          <div className="empty-state">Select or create a note to edit.</div>
        )}
      </main>
    </div>
  );
};
