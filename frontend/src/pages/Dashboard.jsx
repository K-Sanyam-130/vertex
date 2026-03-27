import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import ActionCard from '../components/ActionCard';
import Modal from '../components/Modal';
import OutputConsole from '../components/OutputConsole';
import SerializeModal from '../modals/SerializeModal';
import RestoreModal from '../modals/RestoreModal';
import MergeModal from '../modals/MergeModal';
import GhostModal from '../modals/GhostModal';
import SyncModal from '../modals/SyncModal';

const ACTIONS = [
  {
    id: 'serialize',
    title: 'Serialize',
    description: 'Extract scene data from your .blend file into structured JSON — spatial transforms, materials, lights, and modifiers.',
    icon: '📦',
    badge: 'Extract',
    variant: 'serialize',
  },
  {
    id: 'restore',
    title: 'Restore',
    description: 'Revert your Blender scene to a previously saved version using phased reconstruction.',
    icon: '⏪',
    badge: 'Revert',
    variant: 'restore',
  },
  {
    id: 'merge',
    title: 'Merge',
    description: 'Combine two scene files with union or 3-way merge. Resolve conflicts with configurable strategies.',
    icon: '🔀',
    badge: 'Combine',
    variant: 'merge',
  },
  {
    id: 'ghost',
    title: 'Ghost',
    description: 'Visual diff overlay — see exactly what moved, changed, or was removed as wireframe ghosts.',
    icon: '👻',
    badge: 'Diff',
    variant: 'ghost',
  },
  {
    id: 'sync',
    title: 'Sync',
    description: 'Stage, commit, and push your changes to GitHub in one click. Keep your team in sync.',
    icon: '🔄',
    badge: 'Push',
    variant: 'sync',
  },
];

export default function Dashboard({ apiUrl }) {
  const [activeModal, setActiveModal] = useState(null);
  const [blendFiles, setBlendFiles] = useState([]);
  const [spatialData, setSpatialData] = useState([]);
  const [materialsData, setMaterialsData] = useState([]);
  const [lightingData, setLightingData] = useState([]);
  const [modifiersData, setModifiersData] = useState([]);
  const [user, setUser] = useState(null);

  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // Check for token in URL
    const searchParams = new URLSearchParams(location.search);
    const token = searchParams.get('token') || localStorage.getItem('vertex_token');

    if (token) {
      if (searchParams.has('token')) {
        localStorage.setItem('vertex_token', token);
        navigate('/dashboard', { replace: true });
      }

      fetch(`${apiUrl}/api/auth/user`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(r => r.json())
        .then(data => {
          if (data && data.login) {
            setUser(data);
          }
        })
        .catch(console.error);
    }

    // Fetch blend files
    fetch(`${apiUrl}/api/blend-files`)
      .then(r => r.json())
      .then(setBlendFiles)
      .catch(() => {});

    // Fetch data previews
    fetch(`${apiUrl}/api/data/spatial.json`)
      .then(r => r.json())
      .then(setSpatialData)
      .catch(() => {});

    fetch(`${apiUrl}/api/data/materials.json`)
      .then(r => r.json())
      .then(setMaterialsData)
      .catch(() => {});

    fetch(`${apiUrl}/api/data/lighting.json`)
      .then(r => r.json())
      .then(setLightingData)
      .catch(() => {});

    fetch(`${apiUrl}/api/data/modifiers.json`)
      .then(r => r.json())
      .then(setModifiersData)
      .catch(() => {});
  }, [apiUrl]);

  const closeModal = () => setActiveModal(null);

  const renderModal = () => {
    const props = { apiUrl, blendFiles, onClose: closeModal, user };

    switch (activeModal) {
      case 'serialize': return <SerializeModal {...props} />;
      case 'restore': return <RestoreModal {...props} />;
      case 'merge': return <MergeModal {...props} />;
      case 'ghost': return <GhostModal {...props} />;
      case 'sync': return <SyncModal {...props} />;
      default: return null;
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-secondary)' }}>
      <Navbar 
        isDashboard 
        user={user} 
        onCommitClick={() => setActiveModal('sync')} 
      />

      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Dashboard</h1>
          <p className="dashboard-subtitle">
            Manage your Blender scene version control operations
          </p>
        </div>

        {/* Action Cards */}
        <div className="actions-grid">
          {ACTIONS.map(action => (
            <ActionCard
              key={action.id}
              {...action}
              onClick={() => setActiveModal(action.id)}
            />
          ))}
        </div>

        {/* Data Preview */}
        <div style={{ marginTop: '12px' }}>
          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '20px',
            fontWeight: 600,
            marginBottom: '16px',
            letterSpacing: '-0.3px',
          }}>
            Scene Data
          </h2>

          <div className="data-preview">
            {/* Spatial */}
            <div className="data-card">
              <div className="data-card-header">
                <span className="data-card-title">📍 Objects</span>
                <span className="data-card-count">{spatialData.length}</span>
              </div>
              <div className="data-card-body">
                {spatialData.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">📍</div>
                    <div className="empty-state-text">No spatial data yet</div>
                  </div>
                ) : (
                  spatialData.map((obj, i) => (
                    <div className="data-item" key={i}>
                      <div className="data-item-dot" style={{ background: 'var(--accent-blue)' }} />
                      <span className="data-item-name">{obj.name}</span>
                      <span className="data-item-meta">
                        {obj.loc?.map(v => v.toFixed(1)).join(', ')}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Materials */}
            <div className="data-card">
              <div className="data-card-header">
                <span className="data-card-title">🎨 Materials</span>
                <span className="data-card-count">{materialsData.length}</span>
              </div>
              <div className="data-card-body">
                {materialsData.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">🎨</div>
                    <div className="empty-state-text">No materials data yet</div>
                  </div>
                ) : (
                  materialsData.map((mat, i) => (
                    <div className="data-item" key={i}>
                      <div className="data-item-dot" style={{
                        background: `rgb(${Math.round(mat.base_color[0]*255)}, ${Math.round(mat.base_color[1]*255)}, ${Math.round(mat.base_color[2]*255)})`,
                      }} />
                      <span className="data-item-name">{mat.material_name}</span>
                      <span className="data-item-meta">
                        R:{mat.roughness?.toFixed(1)} M:{mat.metallic?.toFixed(1)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Lights */}
            <div className="data-card">
              <div className="data-card-header">
                <span className="data-card-title">💡 Lights</span>
                <span className="data-card-count">{lightingData.length}</span>
              </div>
              <div className="data-card-body">
                {lightingData.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">💡</div>
                    <div className="empty-state-text">No lighting data yet</div>
                  </div>
                ) : (
                  lightingData.map((light, i) => (
                    <div className="data-item" key={i}>
                      <div className="data-item-dot" style={{ background: 'var(--accent-orange)' }} />
                      <span className="data-item-name">{light.name}</span>
                      <span className="data-item-meta">
                        {light.type} · {light.energy}W
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Modifiers */}
            <div className="data-card">
              <div className="data-card-header">
                <span className="data-card-title">🔧 Modifiers</span>
                <span className="data-card-count">{modifiersData.length}</span>
              </div>
              <div className="data-card-body">
                {modifiersData.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">🔧</div>
                    <div className="empty-state-text">No modifier data yet</div>
                  </div>
                ) : (
                  modifiersData.map((item, i) => (
                    <div className="data-item" key={i}>
                      <div className="data-item-dot" style={{ background: 'var(--accent-purple)' }} />
                      <span className="data-item-name">{item.object_name}</span>
                      <span className="data-item-meta">
                        {item.modifiers?.length} mod{item.modifiers?.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modal */}
      {activeModal && renderModal()}
    </div>
  );
}
