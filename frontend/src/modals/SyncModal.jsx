import { useState } from 'react';
import Modal from '../components/Modal';
import OutputConsole from '../components/OutputConsole';

export default function SyncModal({ apiUrl, onClose }) {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState(null);

  const handleSync = async () => {
    setLoading(true);
    setStatus(null);
    setOutput('');

    try {
      const res = await fetch(`${apiUrl}/api/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message || 'vertex snapshot',
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
    <Modal title="Sync to GitHub" icon="🔄" onClose={onClose}>
      <div className="modal-body">
        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          marginBottom: '20px',
        }}>
          Stage all changes, commit with a message, and push to your remote repository.
        </p>

        <div className="form-group">
          <label className="form-label">Commit Message</label>
          <input
            className="form-input"
            type="text"
            placeholder="vertex snapshot"
            value={message}
            onChange={e => setMessage(e.target.value)}
            id="sync-message-input"
            onKeyDown={e => e.key === 'Enter' && handleSync()}
          />
        </div>

        {status && (
          <div className={`status-badge ${status}`} style={{ marginBottom: '12px' }}>
            {status === 'success' ? '✓ Synced' : '✕ Failed'}
          </div>
        )}

        <OutputConsole output={output} title="Git Output" />
      </div>

      <div className="modal-footer">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button
          className="btn btn-primary"
          onClick={handleSync}
          disabled={loading}
          id="sync-run-btn"
        >
          {loading ? (
            <>
              <span className="spinner" />
              Syncing...
            </>
          ) : (
            'Sync to GitHub'
          )}
        </button>
      </div>
    </Modal>
  );
}
