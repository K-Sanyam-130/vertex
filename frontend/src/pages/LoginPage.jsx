import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';

export default function LoginPage({ apiUrl }) {
  const navigate = useNavigate();

  const handleGitHubLogin = () => {
    window.location.href = `${apiUrl}/api/auth/github`;
  };

  const handleSkipLogin = () => {
    navigate('/dashboard');
  };

  return (
    <div className="login-page">
      {/* Background effects */}
      <div className="login-bg-pattern" />
      <div className="login-grid-overlay" />

      {/* Navigation */}
      <Navbar />

      {/* Hero + Login Card */}
      <div className="login-content">
        <div className="login-hero">
          <div className="login-badge">
            <span className="login-badge-dot" />
            Production Ready v4.2
          </div>

          <h1 className="login-title">
            A more human<br />
            <span className="login-title-accent">way to work</span><br />
            in Blender.
          </h1>

          <p className="login-subtitle">
            The precision of Git meets the spatial intuition of 3D
            artistry. Track every vertex, merge every scene, and
            collaborate without friction.
          </p>

          {/* Feature cards */}
          <div className="login-features">
            <div className="login-feature-card">
              <div className="login-feature-icon">⟳</div>
              <div className="login-feature-title">Real-time syncing</div>
              <div className="login-feature-desc">
                Direct Blender plugin integration for instant commit cycles.
              </div>
            </div>

            <div className="login-feature-card">
              <div className="login-feature-icon">⑂</div>
              <div className="login-feature-title">3-way visual merge</div>
              <div className="login-feature-desc">
                Resolve conflicts spatially with intuitive side-by-side viewports.
              </div>
            </div>

            <div className="login-feature-card login-feature-wide">
              <div className="login-feature-icon">◻</div>
              <div className="login-feature-title">Ghost Box</div>
              <div className="login-feature-desc">
                Isolate specific scene collections for focused data tracking without full-file overhead.
              </div>
            </div>
          </div>
        </div>

        {/* Login Card */}
        <div className="login-card">
          <h2 className="login-card-title">Welcome Back</h2>
          <p className="login-card-subtitle">
            Select your workspace identity to continue.
          </p>

          <button
            className="login-btn login-btn-github"
            onClick={handleGitHubLogin}
            id="btn-github-login"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            Log in with GitHub
          </button>

          <button
            className="login-btn login-btn-blender"
            onClick={handleSkipLogin}
            id="btn-blender-login"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12.51 13.214c.046-.8.438-1.506 1.03-2.006a3.424 3.424 0 012.212-.79c.85-.04 1.655.284 2.25.79.592.5.983 1.206 1.028 2.005.046.8-.268 1.548-.825 2.102-.557.554-1.325.882-2.15.922-.825.04-1.606-.228-2.2-.73-.593-.5-1.004-1.207-1.05-2.007l-.003-.286h.708zm-9.758 0c.046-.8.438-1.506 1.03-2.006a3.424 3.424 0 012.212-.79c.85-.04 1.655.284 2.25.79.592.5.983 1.206 1.028 2.005.046.8-.268 1.548-.825 2.102-.557.554-1.325.882-2.15.922-.825.04-1.606-.228-2.2-.73-.593-.5-1.004-1.207-1.05-2.007l-.003-.286h.708z"/>
            </svg>
            Log in with Blender
          </button>

          <div className="login-card-footer">
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input type="checkbox" style={{ accentColor: 'var(--accent-blue)' }} />
              Remember session
            </label>
            <span style={{ color: 'var(--accent-blue)', cursor: 'pointer', fontSize: '13px' }}>
              Enterprise SSO?
            </span>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="features-section">
        <div className="features-grid">
          <div className="feature-block">
            <div className="feature-block-visual" style={{ background: 'linear-gradient(135deg, #f0f4ff, #e8eeff)' }}>
              <div style={{ textAlign: 'left', padding: '20px', width: '100%' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '12px' }}>LOCAL CHANGES</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-orange)' }} />
                  <span style={{ fontSize: '13px', fontWeight: 500 }}>Main_Body_HighPoly.blend</span>
                  <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--accent-orange)', fontWeight: 600 }}>+2,431 △</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                  <span style={{ fontSize: '13px', fontWeight: 500 }}>Engine_Node_Tree.json</span>
                  <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--accent-green)', fontWeight: 600 }}>NEW</span>
                </div>
                <div style={{ marginTop: '16px', height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: '65%', height: '100%', background: 'var(--gradient-primary)', borderRadius: '3px' }} />
                </div>
              </div>
            </div>
            <h3 className="feature-block-title">Granular Precision</h3>
            <p className="feature-block-desc">
              Unlike standard Git, we analyze the binary structure of
              blend files to show you exactly what changed.
            </p>
          </div>

          <div className="feature-block">
            <div className="feature-block-visual" style={{ background: 'linear-gradient(135deg, #f5f0ff, #ede8ff)' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '48px', marginBottom: '8px' }}>🔮</div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>REV.402</span>
                  <span style={{ fontSize: '11px', padding: '2px 8px', background: 'var(--accent-green)', color: 'white', borderRadius: '4px', fontWeight: 600 }}>CURRENT</span>
                </div>
              </div>
            </div>
            <h3 className="feature-block-title">Spatial Diffs</h3>
            <p className="feature-block-desc">
              Scrub through history visually. See lighting adjustments,
              shader tweaks, and vertex displacements.
            </p>
          </div>

          <div className="feature-block">
            <div className="feature-block-visual" style={{ background: 'linear-gradient(135deg, #fff5f0, #ffe8e0)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', padding: '20px' }}>
                <div style={{ width: '48px', height: '48px', background: 'var(--bg-primary)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px', border: '1px solid var(--border-color)' }}>🖥️</div>
                <div style={{ width: '48px', height: '48px', background: 'var(--bg-primary)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px', border: '1px solid var(--border-color)' }}>☁️</div>
                <div style={{ width: '48px', height: '48px', background: 'var(--bg-primary)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px', border: '1px solid var(--border-color)' }}>🖼️</div>
                <div style={{ width: '48px', height: '48px', background: 'var(--bg-primary)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px', border: '1px solid var(--border-color)' }}>⚡</div>
              </div>
            </div>
            <h3 className="feature-block-title">Technical Rigor</h3>
            <p className="feature-block-desc">
              Built on a distributed architecture that handles multi-terabyte
              project folders with the speed of a local SSD.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="footer">
        <div className="footer-content">
          <div>
            <div className="footer-brand">THE KINETIC WORKSPACE</div>
            <div className="footer-copy">© 2024 Versioning for Creators</div>
          </div>
          <div>
            <div className="footer-col-title">Product</div>
            <a href="#" className="footer-link">Pricing</a>
            <a href="#" className="footer-link">Documentation</a>
            <a href="#" className="footer-link">API Reference</a>
          </div>
          <div>
            <div className="footer-col-title">Legal</div>
            <a href="#" className="footer-link">Privacy Policy</a>
            <a href="#" className="footer-link">Terms of Service</a>
            <a href="#" className="footer-link">Security</a>
          </div>
          <div>
            <div className="footer-col-title">Connect</div>
            <a href="#" className="footer-link">Twitter / X</a>
            <a href="#" className="footer-link">Discord</a>
            <a href="#" className="footer-link">GitHub</a>
          </div>
        </div>
      </div>
    </div>
  );
}
