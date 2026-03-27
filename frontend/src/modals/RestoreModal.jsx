import { useState, useEffect } from 'react';
import Modal from '../components/Modal';
import OutputConsole from '../components/OutputConsole';

export default function RestoreModal({ apiUrl, blendFiles, onClose }) {
  const [selectedFile, setSelectedFile] = useState(blendFiles[0]?.name || '');
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState('');
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/versions?domain=spatial`)
      .then(r => r.json())
      .then(data => {
        setVersions(data);
        if (data.length > 0) {
          setSelectedVersion(String(data[data.length - 1].version));
        }
      })
      .catch(() => {});
  }, [apiUrl]);

  const handleRun = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setStatus(null);
    setOutput('');

    try {
      const res = await fetch(`${apiUrl}/api/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blendFile: selectedFile,
          version: selectedVersion || undefined,
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
    <Modal title="Restore" icon="⏪" onClose={onClose}>
      <div className="modal-body">
        <div className="form-group">
          <label className="form-label">Blend File</label>
          <select
            className="form-select"
            value={selectedFile}
            onChange={e => setSelectedFile(e.target.value)}
            id="restore-file-select"
          >
            <option value="">Select a .blend file</option>
            {blendFiles.map(f => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Version</label>
          {versions.length === 0 ? (
            <div style={{
              padding: '12px',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              color: 'var(--text-tertiary)',
            }}>
              No version history found. Run Serialize at least twice to build history.
            </div>
          ) : (
            <select
              className="form-select"
              value={selectedVersion}
              onChange={e => setSelectedVersion(e.target.value)}
              id="restore-version-select"
            >
              {versions.map(v => (
                <option key={v.version} value={v.version}>
                  v{v.version} — {v.domain} {v.isMerge ? '[MERGE]' : ''} — {new Date(v.timestamp).toLocaleString()}
                </option>
              ))}
            </select>
          )}
        </div>

        {status && (
          <div className={`status-badge ${status}`} style={{ marginBottom: '12px' }}>
            {status === 'success' ? '✓ Restored' : '✕ Failed'}
          </div>
        )}

        <OutputConsole output={output} title="Restore Output" />
      </div>

      <div className="modal-footer">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button
          className="btn btn-primary"
          onClick={handleRun}
          disabled={loading || !selectedFile}
          id="restore-run-btn"
        >
          {loading ? (
            <>
              <span className="spinner" />
              Restoring...
            </>
          ) : (
            'Restore Scene'
          )}
        </button>
      </div>
    </Modal>
  );
}
