/**
 * Semantic Badge component
 */
import { HTMLAttributes, ReactNode } from 'react'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'
  children: ReactNode
}

export const Badge = ({ variant = 'primary', children, className = '', ...props }: BadgeProps) => {
  const variantClass = `badge-${variant}`
  return (
    <span className={`${variantClass} ${className}`.trim()} {...props}>
      {children}
    </span>
  )
}
