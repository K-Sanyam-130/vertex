import { useNavigate, useLocation } from 'react-router-dom';

export default function Navbar({ isDashboard, user, onCommitClick }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className="navbar">
      <div
        className="navbar-logo"
        style={{ cursor: 'pointer' }}
        onClick={() => navigate('/login')}
      >
        <div className="navbar-logo-icon">⬡</div>
        THE KINETIC WORKSPACE
      </div>

      {isDashboard ? (
        <>
          <div className="navbar-links">
            <button
              className={`navbar-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
              onClick={() => navigate('/dashboard')}
            >
              Projects
            </button>
            <button className="navbar-link">Merge Hub</button>
            <button className="navbar-link">Activity</button>
            <button className="navbar-link">Settings</button>
          </div>

          <div className="navbar-actions">
            {user ? (
              <div className="navbar-user">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="Avatar" className="navbar-avatar" />
                ) : (
                  <div className="navbar-avatar">{user.login?.[0]?.toUpperCase() || 'U'}</div>
                )}
                <span className="navbar-username">{user.login}</span>
              </div>
            ) : null}
            <button className="btn btn-outline btn-sm" style={{ borderRadius: '100px' }}>
              🔔
            </button>
            <button className="btn btn-outline btn-sm" style={{ borderRadius: '100px' }}>
              ❓
            </button>
            <button
              className="btn btn-primary btn-sm"
              style={{ borderRadius: '100px' }}
              onClick={onCommitClick}
            >
              Commit
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="navbar-links">
            <button className="navbar-link">Projects</button>
            <button className="navbar-link">Merge Hub</button>
            <button className="navbar-link">Activity</button>
            <button className="navbar-link">Settings</button>
          </div>

          <div className="navbar-actions">
            <button className="btn btn-outline btn-sm" style={{ borderRadius: '100px' }}>
              🔔
            </button>
            <button className="btn btn-outline btn-sm" style={{ borderRadius: '100px' }}>
              ❓
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => navigate('/dashboard')}
              style={{ borderRadius: '100px' }}
            >
              Commit
            </button>
          </div>
        </>
      )}
    </nav>
  );
}
