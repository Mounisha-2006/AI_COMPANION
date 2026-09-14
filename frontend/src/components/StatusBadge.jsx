import React from 'react';

export function StatusBadge({ status }) {
  const normalized = (status || 'queued').toLowerCase();

  switch (normalized) {
    case 'queued':
      return (
        <span className="badge badge-queued">
          <span>⏳</span> Queued
        </span>
      );
    case 'processing':
      return (
        <span className="badge badge-processing">
          <span className="spinner" style={{ width: 10, height: 10, borderWidth: 2 }}></span> Processing
        </span>
      );
    case 'ready':
      return (
        <span className="badge badge-ready">
          <span>✓</span> Ready
        </span>
      );
    case 'failed':
      return (
        <span className="badge badge-failed">
          <span>✕</span> Failed
        </span>
      );
    default:
      return <span className="badge">{status}</span>;
  }
}
