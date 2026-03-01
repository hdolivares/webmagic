/**
 * ConfirmModal — reusable confirmation dialog.
 *
 * Replaces native `confirm()` dialogs with a properly styled, accessible
 * overlay modal.  Callers control the title, message, button labels, and
 * visual variant.  The modal closes on Escape or backdrop click.
 *
 * Usage pattern (single `pendingAction` state per page):
 *
 *   const [pendingAction, setPendingAction] = useState<ConfirmAction | null>(null)
 *
 *   // To open:
 *   setPendingAction({
 *     title: 'Regenerate Site?',
 *     message: 'This will clear the existing HTML and re-run the full AI pipeline.',
 *     confirmLabel: 'Yes, Regenerate',
 *     variant: 'warning',
 *     onConfirm: () => regenMutation.mutate(site.id),
 *   })
 *
 *   // In JSX:
 *   {pendingAction && (
 *     <ConfirmModal
 *       {...pendingAction}
 *       isLoading={regenMutation.isPending}
 *       onCancel={() => setPendingAction(null)}
 *     />
 *   )}
 */
import { useEffect, useCallback } from 'react'
import { AlertTriangle, AlertCircle, HelpCircle, Loader2 } from 'lucide-react'

export type ConfirmVariant = 'danger' | 'warning' | 'default'

export interface ConfirmAction {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: ConfirmVariant
  onConfirm: () => void
}

interface ConfirmModalProps extends ConfirmAction {
  isLoading?: boolean
  onCancel: () => void
}

const VARIANT_CONFIG: Record<
  ConfirmVariant,
  { icon: React.ReactNode; confirmClass: string; iconClass: string }
> = {
  danger: {
    icon: <AlertCircle className="w-6 h-6" />,
    confirmClass: 'bg-error hover:bg-error-dark text-white disabled:opacity-50',
    iconClass: 'text-error bg-error-light',
  },
  warning: {
    icon: <AlertTriangle className="w-6 h-6" />,
    confirmClass: 'bg-warning hover:bg-warning-dark text-white disabled:opacity-50',
    iconClass: 'text-warning-dark bg-warning-light',
  },
  default: {
    icon: <HelpCircle className="w-6 h-6" />,
    confirmClass: 'bg-primary-600 hover:bg-primary-700 text-white disabled:opacity-50',
    iconClass: 'text-primary-600 bg-primary-100',
  },
}

export function ConfirmModal({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const cfg = VARIANT_CONFIG[variant]

  // Close on Escape
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) onCancel()
    },
    [isLoading, onCancel],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [handleKey])

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-black/50 p-md"
      onClick={() => { if (!isLoading) onCancel() }}
    >
      {/* Dialog */}
      <div
        className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md p-lg space-y-md"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        aria-describedby="confirm-modal-message"
      >
        {/* Icon + title */}
        <div className="flex items-start gap-md">
          <span className={`p-sm rounded-lg flex-shrink-0 ${cfg.iconClass}`}>
            {cfg.icon}
          </span>
          <h3
            id="confirm-modal-title"
            className="text-base font-semibold text-text-primary leading-snug pt-xs"
          >
            {title}
          </h3>
        </div>

        {/* Message */}
        <p
          id="confirm-modal-message"
          className="text-sm text-text-secondary leading-relaxed"
        >
          {message}
        </p>

        {/* Buttons */}
        <div className="flex gap-sm justify-end pt-xs">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-md py-sm text-sm rounded-md border border-border text-text-secondary hover:bg-bg-secondary transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-md py-sm text-sm rounded-md font-medium transition-colors flex items-center gap-xs ${cfg.confirmClass}`}
          >
            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
