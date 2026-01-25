/**
 * PasswordStrengthIndicator Component
 * 
 * Visual indicator showing password strength with requirements checklist.
 * Follows semantic CSS and accessibility best practices.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React from 'react'
import './PasswordStrengthIndicator.css'

export type PasswordStrength = 'weak' | 'medium' | 'strong'

interface PasswordStrengthIndicatorProps {
  password: string
  showRequirements?: boolean
}

export interface PasswordValidation {
  hasMinLength: boolean
  hasLetter: boolean
  hasNumber: boolean
  hasUpperCase: boolean
  hasSpecialChar: boolean
  strength: PasswordStrength
}

/**
 * Calculate password strength and validation requirements
 */
export const calculatePasswordStrength = (password: string): PasswordValidation => {
  const hasMinLength = password.length >= 8
  const hasLetter = /[a-zA-Z]/.test(password)
  const hasNumber = /\d/.test(password)
  const hasUpperCase = /[A-Z]/.test(password)
  const hasSpecialChar = /[^a-zA-Z0-9]/.test(password)

  // Calculate strength score
  let strengthScore = 0
  if (hasMinLength) strengthScore++
  if (hasLetter) strengthScore++
  if (hasNumber) strengthScore++
  if (hasUpperCase) strengthScore++
  if (hasSpecialChar) strengthScore++

  // Determine strength level
  let strength: PasswordStrength = 'weak'
  if (strengthScore >= 5) {
    strength = 'strong'
  } else if (strengthScore >= 3) {
    strength = 'medium'
  }

  return {
    hasMinLength,
    hasLetter,
    hasNumber,
    hasUpperCase,
    hasSpecialChar,
    strength,
  }
}

const PasswordStrengthIndicator: React.FC<PasswordStrengthIndicatorProps> = ({
  password,
  showRequirements = true,
}) => {
  const validation = calculatePasswordStrength(password)

  if (!password) {
    return null
  }

  const getStrengthColor = () => {
    switch (validation.strength) {
      case 'strong':
        return 'strength-strong'
      case 'medium':
        return 'strength-medium'
      case 'weak':
      default:
        return 'strength-weak'
    }
  }

  const getStrengthText = () => {
    switch (validation.strength) {
      case 'strong':
        return 'Strong password'
      case 'medium':
        return 'Medium strength'
      case 'weak':
      default:
        return 'Weak password'
    }
  }

  const getStrengthPercentage = () => {
    switch (validation.strength) {
      case 'strong':
        return 100
      case 'medium':
        return 60
      case 'weak':
      default:
        return 30
    }
  }

  return (
    <div className="password-strength-indicator">
      {/* Strength Bar */}
      <div className="strength-bar-container" role="progressbar" aria-valuenow={getStrengthPercentage()} aria-valuemin={0} aria-valuemax={100} aria-label={`Password strength: ${getStrengthText()}`}>
        <div className="strength-bar-background">
          <div
            className={`strength-bar-fill ${getStrengthColor()}`}
            style={{ width: `${getStrengthPercentage()}%` }}
          />
        </div>
        <span className={`strength-text ${getStrengthColor()}`}>
          {getStrengthText()}
        </span>
      </div>

      {/* Requirements Checklist */}
      {showRequirements && (
        <div className="password-requirements">
          <p className="requirements-title">Password must contain:</p>
          <ul className="requirements-list">
            <li className={validation.hasMinLength ? 'requirement-met' : 'requirement-unmet'}>
              <span className="requirement-icon" aria-hidden="true">
                {validation.hasMinLength ? '✓' : '○'}
              </span>
              <span>At least 8 characters</span>
            </li>
            <li className={validation.hasLetter ? 'requirement-met' : 'requirement-unmet'}>
              <span className="requirement-icon" aria-hidden="true">
                {validation.hasLetter ? '✓' : '○'}
              </span>
              <span>At least one letter</span>
            </li>
            <li className={validation.hasNumber ? 'requirement-met' : 'requirement-unmet'}>
              <span className="requirement-icon" aria-hidden="true">
                {validation.hasNumber ? '✓' : '○'}
              </span>
              <span>At least one number</span>
            </li>
          </ul>
        </div>
      )}
    </div>
  )
}

export default PasswordStrengthIndicator
