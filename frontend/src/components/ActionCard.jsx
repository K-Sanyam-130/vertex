export default function ActionCard({ title, description, icon, badge, variant, onClick }) {
  return (
    <div
      className="action-card"
      data-variant={variant}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      id={`action-card-${variant}`}
    >
      {badge && <span className="action-card-badge">{badge}</span>}
      <div className="action-card-icon">{icon}</div>
      <h3 className="action-card-title">{title}</h3>
      <p className="action-card-desc">{description}</p>
    </div>
  );
}
