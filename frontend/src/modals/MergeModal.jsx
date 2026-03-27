import { useState, useEffect } from 'react';
import Modal from '../components/Modal';
import OutputConsole from '../components/OutputConsole';

export default function MergeModal({ apiUrl, blendFiles, onClose }) {
  const [selectedFile, setSelectedFile] = useState(blendFiles[0]?.name || '');
  const [fileA, setFileA] = useState('');
  const [fileB, setFileB] = useState('');
  const [mode, setMode] = useState('union');
  const [strategy, setStrategy] = useState('theirs');
  const [jsonFiles, setJsonFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState(null);

  useEffect(() => {
    // List JSON files in data/ that could be used for merging
    fetch(`${apiUrl}/api/data/spatial.json`)
      .then(() => {
        // We know spatial.json exists, let's build a list from blend files
        const files = blendFiles.map(f => `data/${f.name.replace('.blend', '.json')}`);
        files.push('data/spatial.json');
        setJsonFiles([...new Set(files)]);
      })
      .catch(() => {});
  }, [apiUrl, blendFiles]);

  const handleRun = async () => {
    if (!selectedFile || !fileA || !fileB) return;
    setLoading(true);
    setStatus(null);
    setOutput('');

    try {
      const res = await fetch(`${apiUrl}/api/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blendFile: selectedFile,
          fileA,
          fileB,
          mode,
          strategy: mode === '3way' ? strategy : undefined,
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
    <Modal title="Merge" icon="🔀" onClose={onClose}>
      <div className="modal-body">
        <div className="form-group">
          <label className="form-label">Blend File</label>
          <select
            className="form-select"
            value={selectedFile}
            onChange={e => setSelectedFile(e.target.value)}
          >
            <option value="">Select a .blend file</option>
            {blendFiles.map(f => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="form-group">
            <label className="form-label">File A (JSON)</label>
            <input
              className="form-input"
              type="text"
              placeholder="data/fileA.json"
              value={fileA}
              onChange={e => setFileA(e.target.value)}
              list="json-files-a"
            />
            <datalist id="json-files-a">
              {jsonFiles.map(f => <option key={f} value={f} />)}
            </datalist>
          </div>

          <div className="form-group">
            <label className="form-label">File B (JSON)</label>
            <input
              className="form-input"
              type="text"
              placeholder="data/fileB.json"
              value={fileB}
              onChange={e => setFileB(e.target.value)}
              list="json-files-b"
            />
            <datalist id="json-files-b">
              {jsonFiles.map(f => <option key={f} value={f} />)}
            </datalist>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Merge Mode</label>
          <div className="form-radio-group">
            <button
              className={`form-radio-btn ${mode === 'union' ? 'active' : ''}`}
              onClick={() => setMode('union')}
            >
              Union
            </button>
            <button
              className={`form-radio-btn ${mode === '3way' ? 'active' : ''}`}
              onClick={() => setMode('3way')}
            >
              3-Way
            </button>
          </div>
        </div>

        {mode === '3way' && (
          <div className="form-group">
            <label className="form-label">Conflict Strategy</label>
            <div className="form-radio-group">
              <button
                className={`form-radio-btn ${strategy === 'ours' ? 'active' : ''}`}
                onClick={() => setStrategy('ours')}
              >
                Ours (File A)
              </button>
              <button
                className={`form-radio-btn ${strategy === 'theirs' ? 'active' : ''}`}
                onClick={() => setStrategy('theirs')}
              >
                Theirs (File B)
              </button>
            </div>
          </div>
        )}

        {status && (
          <div className={`status-badge ${status}`} style={{ marginBottom: '12px' }}>
            {status === 'success' ? '✓ Merged' : '✕ Failed'}
          </div>
        )}

        <OutputConsole output={output} title="Merge Output" />
      </div>

      <div className="modal-footer">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button
          className="btn btn-primary"
          onClick={handleRun}
          disabled={loading || !selectedFile || !fileA || !fileB}
          id="merge-run-btn"
        >
          {loading ? (
            <>
              <span className="spinner" />
              Merging...
            </>
          ) : (
            'Run Merge'
          )}
        </button>
      </div>
    </Modal>
  );
}
