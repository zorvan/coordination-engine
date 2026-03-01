/**
 * Reusable Alert/Message components.
 */

import React from 'react'

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  onClose?: () => void
  children: React.ReactNode
}

export const Alert: React.FC<AlertProps> = ({
  type,
  title,
  onClose,
  children,
  className = '',
  ...props
}) => (
  <div className={`alert alert-${type} ${className}`.trim()} {...props}>
    <div className="alert-content">
      {title && <h4>{title}</h4>}
      <p>{children}</p>
    </div>
    {onClose && (
      <button type="button" className="close-btn" onClick={onClose}>
        ×
      </button>
    )}
  </div>
)

export interface LoadingProps {
  message?: string
}

export const Loading: React.FC<LoadingProps> = ({ message = 'Loading...' }) => (
  <div className="loading">
    <div className="spinner" />
    <p>{message}</p>
  </div>
)

export interface EmptyStateProps {
  title: string
  message?: string
  icon?: string
  action?: React.ReactNode
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  icon,
  action,
}) => (
  <div className="empty-state">
    {icon && <div className="icon">{icon}</div>}
    <h3>{title}</h3>
    {message && <p>{message}</p>}
    {action && <div className="action">{action}</div>}
  </div>
)
