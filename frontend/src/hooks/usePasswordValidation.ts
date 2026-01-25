/**
 * usePasswordValidation Hook
 * 
 * Custom hook for password validation and strength checking.
 * Returns validation state and helper functions.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import { useState, useEffect } from 'react'
import { calculatePasswordStrength, PasswordValidation } from '../components/PasswordStrengthIndicator/PasswordStrengthIndicator'

interface UsePasswordValidationOptions {
  minLength?: number
  requireLetter?: boolean
  requireNumber?: boolean
  requireUpperCase?: boolean
  requireSpecialChar?: boolean
}

interface UsePasswordValidationReturn extends PasswordValidation {
  isValid: boolean
  errorMessage: string | null
}

/**
 * Hook to validate password requirements and calculate strength
 * 
 * @param password - The password to validate
 * @param options - Validation options (defaults to basic requirements)
 * @returns Validation state with strength and error message
 */
export const usePasswordValidation = (
  password: string,
  options: UsePasswordValidationOptions = {}
): UsePasswordValidationReturn => {
  const {
    minLength = 8,
    requireLetter = true,
    requireNumber = true,
    requireUpperCase = false,
    requireSpecialChar = false,
  } = options

  const [validation, setValidation] = useState<UsePasswordValidationReturn>({
    hasMinLength: false,
    hasLetter: false,
    hasNumber: false,
    hasUpperCase: false,
    hasSpecialChar: false,
    strength: 'weak',
    isValid: false,
    errorMessage: null,
  })

  useEffect(() => {
    if (!password) {
      setValidation({
        hasMinLength: false,
        hasLetter: false,
        hasNumber: false,
        hasUpperCase: false,
        hasSpecialChar: false,
        strength: 'weak',
        isValid: false,
        errorMessage: null,
      })
      return
    }

    const strengthValidation = calculatePasswordStrength(password)
    
    // Check if all required conditions are met
    const meetsMinLength = password.length >= minLength
    const meetsLetterRequirement = !requireLetter || strengthValidation.hasLetter
    const meetsNumberRequirement = !requireNumber || strengthValidation.hasNumber
    const meetsUpperCaseRequirement = !requireUpperCase || strengthValidation.hasUpperCase
    const meetsSpecialCharRequirement = !requireSpecialChar || strengthValidation.hasSpecialChar

    const isValid =
      meetsMinLength &&
      meetsLetterRequirement &&
      meetsNumberRequirement &&
      meetsUpperCaseRequirement &&
      meetsSpecialCharRequirement

    // Generate error message
    let errorMessage: string | null = null
    if (!isValid && password.length > 0) {
      const missingRequirements: string[] = []
      
      if (!meetsMinLength) {
        missingRequirements.push(`at least ${minLength} characters`)
      }
      if (!meetsLetterRequirement) {
        missingRequirements.push('a letter')
      }
      if (!meetsNumberRequirement) {
        missingRequirements.push('a number')
      }
      if (!meetsUpperCaseRequirement) {
        missingRequirements.push('an uppercase letter')
      }
      if (!meetsSpecialCharRequirement) {
        missingRequirements.push('a special character')
      }

      if (missingRequirements.length > 0) {
        errorMessage = `Password must contain ${missingRequirements.join(', ')}`
      }
    }

    setValidation({
      ...strengthValidation,
      isValid,
      errorMessage,
    })
  }, [password, minLength, requireLetter, requireNumber, requireUpperCase, requireSpecialChar])

  return validation
}

/**
 * Validate if two passwords match
 * 
 * @param password - The password
 * @param confirmPassword - The confirmation password
 * @returns Error message if passwords don't match, null otherwise
 */
export const validatePasswordMatch = (
  password: string,
  confirmPassword: string
): string | null => {
  if (!confirmPassword) {
    return null
  }
  
  if (password !== confirmPassword) {
    return 'Passwords do not match'
  }
  
  return null
}

/**
 * Validate complete password form (password + confirmation)
 * 
 * @param password - The password
 * @param confirmPassword - The confirmation password
 * @param validation - The password validation state from usePasswordValidation
 * @returns Error message if validation fails, null otherwise
 */
export const validatePasswordForm = (
  password: string,
  confirmPassword: string,
  validation: UsePasswordValidationReturn
): string | null => {
  if (!password) {
    return 'Password is required'
  }

  if (!validation.isValid) {
    return validation.errorMessage || 'Password does not meet requirements'
  }

  const matchError = validatePasswordMatch(password, confirmPassword)
  if (matchError) {
    return matchError
  }

  return null
}
