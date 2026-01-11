/**
 * Semantic Card component
 */
import { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  children: ReactNode
}

export const Card = ({ hover = false, children, className = '', ...props }: CardProps) => {
  const baseClass = hover ? 'card-hover' : 'card'
  return (
    <div className={`${baseClass} ${className}`.trim()} {...props}>
      {children}
    </div>
  )
}

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export const CardHeader = ({ children, className = '', ...props }: CardHeaderProps) => (
  <div className={`card-header ${className}`.trim()} {...props}>
    {children}
  </div>
)

interface CardBodyProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export const CardBody = ({ children, className = '', ...props }: CardBodyProps) => (
  <div className={`card-body ${className}`.trim()} {...props}>
    {children}
  </div>
)

interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export const CardFooter = ({ children, className = '', ...props }: CardFooterProps) => (
  <div className={`card-footer ${className}`.trim()} {...props}>
    {children}
  </div>
)

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  children: ReactNode
}

export const CardTitle = ({ children, className = '', ...props }: CardTitleProps) => (
  <h3 className={`card-title ${className}`.trim()} {...props}>
    {children}
  </h3>
)

interface CardSubtitleProps extends HTMLAttributes<HTMLParagraphElement> {
  children: ReactNode
}

export const CardSubtitle = ({ children, className = '', ...props }: CardSubtitleProps) => (
  <p className={`card-subtitle ${className}`.trim()} {...props}>
    {children}
  </p>
)
