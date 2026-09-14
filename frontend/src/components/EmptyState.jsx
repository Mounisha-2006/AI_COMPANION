import React from 'react';

export function EmptyState({ icon = '📂', title, description, action }) {
  return (
    <div className="empty-state">
      <div style={{ fontSize: 40, lineHeight: 1 }}>{icon}</div>
      <h4 className="empty-title">{title}</h4>
      {description && <p className="empty-desc">{description}</p>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}
