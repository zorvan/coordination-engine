/**
 * Reusable Form components.
 */

import React from 'react'

export interface FormProps extends React.FormHTMLAttributes<HTMLFormElement> {
  children: React.ReactNode
}

export const Form = React.forwardRef<HTMLFormElement, FormProps>(
  ({ className = '', children, ...props }, ref) => (
    <form ref={ref} className={`form ${className}`.trim()} {...props}>
      {children}
    </form>
  )
)

Form.displayName = 'Form'

export interface FormGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string
  error?: string
  required?: boolean
  children: React.ReactNode
}

export const FormGroup = React.forwardRef<HTMLDivElement, FormGroupProps>(
  ({ label, error, required = false, className = '', children, ...props }, ref) => (
    <div ref={ref} className={`form-group ${error ? 'error' : ''} ${className}`.trim()} {...props}>
      {label && (
        <label>
          {label}
          {required && <span className="required">*</span>}
        </label>
      )}
      {children}
      {error && <span className="error-message">{error}</span>}
    </div>
  )
)

FormGroup.displayName = 'FormGroup'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => (
    <>
      {label && <label htmlFor={props.id}>{label}</label>}
      <input ref={ref} className={`input ${error ? 'error' : ''} ${className}`.trim()} {...props} />
      {error && <span className="error-message">{error}</span>}
    </>
  )
)

Input.displayName = 'Input'

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ label, error, className = '', ...props }, ref) => (
    <>
      {label && <label htmlFor={props.id}>{label}</label>}
      <textarea ref={ref} className={`input ${error ? 'error' : ''} ${className}`.trim()} {...props} />
      {error && <span className="error-message">{error}</span>}
    </>
  )
)

TextArea.displayName = 'TextArea'

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: Array<{ label: string; value: string }>
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className = '', ...props }, ref) => (
    <>
      {label && <label htmlFor={props.id}>{label}</label>}
      <select ref={ref} className={`input ${error ? 'error' : ''} ${className}`.trim()} {...props}>
        <option value="">Select an option</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <span className="error-message">{error}</span>}
    </>
  )
)

Select.displayName = 'Select'
