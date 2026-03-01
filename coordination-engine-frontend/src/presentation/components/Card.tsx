/**
 * Reusable Card component.
 */

import React from 'react'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`card ${className}`.trim()} {...props}>
      {children}
    </div>
  )
)

Card.displayName = 'Card'

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  subtitle?: string
  action?: React.ReactNode
  children?: React.ReactNode
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, subtitle, action, className = '', children, ...props }, ref) => (
    <div ref={ref} className={`card-head ${className}`.trim()} {...props}>
      <div>
        {title && <h3>{title}</h3>}
        {subtitle && <p className="subtle">{subtitle}</p>}
        {children}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
)

CardHeader.displayName = 'CardHeader'

export interface CardBodyProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const CardBody = React.forwardRef<HTMLDivElement, CardBodyProps>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`card-body ${className}`.trim()} {...props}>
      {children}
    </div>
  )
)

CardBody.displayName = 'CardBody'

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`card-footer ${className}`.trim()} {...props}>
      {children}
    </div>
  )
)

CardFooter.displayName = 'CardFooter'
