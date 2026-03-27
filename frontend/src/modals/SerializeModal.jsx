import { useState } from 'react';
import Modal from '../components/Modal';
import OutputConsole from '../components/OutputConsole';

export default function SerializeModal({ apiUrl, blendFiles, onClose, user }) {
  const [selectedFile, setSelectedFile] = useState(blendFiles[0]?.name || '');
  const [userName, setUserName] = useState(user?.login || '');
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState(null);

  const handleRun = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setStatus(null);
    setOutput('');

    try {
      const res = await fetch(`${apiUrl}/api/serialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blendFile: selectedFile,
          user: userName || undefined,
        }),
      });
      const data = await res.json();
      setOutput(data.output || data.errors || 'No output');
      setStatus(data.success ? 'success' : 'error');
    } catch (err) {
      setOutput(`Request failed: ${err.message}`);
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Serialize" icon="📦" onClose={onClose}>
      <div className="modal-body">
        <div className="form-group">
          <label className="form-label">Blend File</label>
          <select
            className="form-select"
            value={selectedFile}
            onChange={e => setSelectedFile(e.target.value)}
            id="serialize-file-select"
          >
            <option value="">Select a .blend file</option>
            {blendFiles.map(f => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">
            User Name <span className="form-label-hint">(optional)</span>
          </label>
          <input
            className="form-input"
            type="text"
            placeholder="e.g. sanyam"
            value={userName}
            onChange={e => setUserName(e.target.value)}
            id="serialize-user-input"
          />
        </div>

        {status && (
          <div className={`status-badge ${status}`} style={{ marginBottom: '12px' }}>
            {status === 'success' ? '✓ Completed' : '✕ Failed'}
          </div>
        )}

        <OutputConsole output={output} title="Serialize Output" />
      </div>

      <div className="modal-footer">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button
          className="btn btn-primary"
          onClick={handleRun}
          disabled={loading || !selectedFile}
          id="serialize-run-btn"
        >
          {loading ? (
            <>
              <span className="spinner" />
              Running...
            </>
          ) : (
            'Run Serialize'
          )}
        </button>
      </div>
    </Modal>
  );
}
