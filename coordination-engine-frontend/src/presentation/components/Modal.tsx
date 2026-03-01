/**
 * Reusable Modal component.
 */

import React from 'react'

export interface ModalProps {
  open: boolean
  title?: string
  onClose: () => void
  children: React.ReactNode
  footer?: React.ReactNode
}

export const Modal: React.FC<ModalProps> = ({
  open,
  title,
  onClose,
  children,
  footer,
}) => {
  if (!open) return null

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal">
        {title && (
          <div className="modal-header">
            <h2>{title}</h2>
            <button type="button" className="close-btn" onClick={onClose}>×</button>
          </div>
        )}
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </>
  )
}
