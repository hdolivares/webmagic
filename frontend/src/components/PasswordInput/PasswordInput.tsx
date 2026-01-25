/**
 * PasswordInput Component
 * 
 * Reusable password input with visibility toggle.
 * Follows semantic CSS and accessibility best practices.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React, { useState } from 'react'
import './PasswordInput.css'

interface PasswordInputProps {
  id: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  label: string
  placeholder?: string
  error?: string
  hint?: string
  required?: boolean
  autoComplete?: string
  disabled?: boolean
  'aria-describedby'?: string
}

const PasswordInput: React.FC<PasswordInputProps> = ({
  id,
  value,
  onChange,
  label,
  placeholder = '',
  error,
  hint,
  required = false,
  autoComplete = 'current-password',
  disabled = false,
  'aria-describedby': ariaDescribedby,
}) => {
  const [showPassword, setShowPassword] = useState(false)

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  // Build aria-describedby attribute
  const describedByIds: string[] = []
  if (hint) describedByIds.push(`${id}-hint`)
  if (error) describedByIds.push(`${id}-error`)
  if (ariaDescribedby) describedByIds.push(ariaDescribedby)
  const describedBy = describedByIds.length > 0 ? describedByIds.join(' ') : undefined

  return (
    <div className="password-input-wrapper">
      <label htmlFor={id} className="password-input-label">
        {label}
        {required && (
          <span className="required-indicator" aria-label="required">
            *
          </span>
        )}
      </label>

      <div className="password-input-container">
        <input
          id={id}
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          disabled={disabled}
          required={required}
          aria-required={required}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={`password-input ${error ? 'password-input-error' : ''}`}
        />

        <button
          type="button"
          onClick={togglePasswordVisibility}
          className="password-toggle-btn"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
          tabIndex={0}
        >
          {showPassword ? (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>

      {hint && !error && (
        <div id={`${id}-hint`} className="password-input-hint">
          {hint}
        </div>
      )}

      {error && (
        <div id={`${id}-error`} className="password-input-error-text" role="alert">
          {error}
        </div>
      )}
    </div>
  )
}

export default PasswordInput
