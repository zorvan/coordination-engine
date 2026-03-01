/**
 * Reusable Button component.
 */

import React from 'react'

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'icon'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: React.ReactNode
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, className = '', children, disabled, ...props }, ref) => {
    const variantClass = `btn ${variant}`
    const sizeClass = size ? `size-${size}` : ''
    const disabledClass = disabled || loading ? 'disabled' : ''
    
    return (
      <button
        ref={ref}
        type={props.type ?? 'button'}
        className={`${variantClass} ${sizeClass} ${disabledClass} ${className}`.trim()}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? <span>...</span> : children}
      </button>
    )
  }
)

Button.displayName = 'Button'
