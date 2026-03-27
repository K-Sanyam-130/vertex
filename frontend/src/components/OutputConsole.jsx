import { useRef, useEffect } from 'react';

function classifyLine(line) {
  if (line.includes('✅') || line.includes('success') || line.includes('Saved')) return 'output-line-success';
  if (line.includes('❌') || line.includes('error') || line.includes('Error') || line.includes('ERROR')) return 'output-line-error';
  if (line.includes('⚠') || line.includes('WARNING') || line.includes('warn')) return 'output-line-warning';
  if (line.includes('[Vertex]') || line.includes('ℹ')) return 'output-line-info';
  return '';
}

export default function OutputConsole({ output, title = 'Output' }) {
  const bodyRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [output]);

  if (!output) return null;

  const lines = output.split('\n');

  return (
    <div className="output-console">
      <div className="output-console-header">
        <span className="output-console-dot red" />
        <span className="output-console-dot yellow" />
        <span className="output-console-dot green" />
        <span className="output-console-title">{title}</span>
      </div>
      <div className="output-console-body" ref={bodyRef}>
        {lines.map((line, i) => (
          <div key={i} className={classifyLine(line)}>
            {line || '\u00A0'}
          </div>
        ))}
      </div>
    </div>
  );
}
