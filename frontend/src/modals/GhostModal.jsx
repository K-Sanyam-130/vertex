import { useState } from 'react';
import Modal from '../components/Modal';
import OutputConsole from '../components/OutputConsole';

export default function GhostModal({ apiUrl, blendFiles, onClose }) {
  const [selectedFile, setSelectedFile] = useState(blendFiles[0]?.name || '');
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState(null);

  const handleRun = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setStatus(null);
    setOutput('');

    try {
      const res = await fetch(`${apiUrl}/api/ghost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blendFile: selectedFile }),
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
    <Modal title="Ghost Diff" icon="👻" onClose={onClose}>
      <div className="modal-body">
        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          marginBottom: '20px',
        }}>
          Compare the live Blender scene against the last saved state. 
          Changed or removed objects appear as semi-transparent green 
          wireframe "ghosts" in the viewport.
        </p>

        <div className="form-group">
          <label className="form-label">Blend File</label>
          <select
            className="form-select"
            value={selectedFile}
            onChange={e => setSelectedFile(e.target.value)}
            id="ghost-file-select"
          >
            <option value="">Select a .blend file</option>
            {blendFiles.map(f => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>
        </div>

        {status && (
          <div className={`status-badge ${status}`} style={{ marginBottom: '12px' }}>
            {status === 'success' ? '✓ Ghosts Generated' : '✕ Failed'}
          </div>
        )}

        <OutputConsole output={output} title="Ghost Output" />
      </div>

      <div className="modal-footer">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button
          className="btn btn-primary"
          onClick={handleRun}
          disabled={loading || !selectedFile}
          id="ghost-run-btn"
        >
          {loading ? (
            <>
              <span className="spinner" />
              Generating...
            </>
          ) : (
            'Generate Ghosts'
          )}
        </button>
      </div>
    </Modal>
  );
}
