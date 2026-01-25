# Password Management Implementation Plan

## Executive Summary

Implement comprehensive password management features for the customer portal, including:
1. **Forgot Password** - Allow customers to reset forgotten passwords via email
2. **Change Password** - Enable logged-in customers to update their passwords
3. **Email Templates** - Professional email communications for password operations

---

## Current State Analysis

### ✅ Backend Implementation (Complete)

The backend already has all necessary endpoints implemented in `backend/api/v1/customer_auth.py`:

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/customer/forgot-password` | POST | Request password reset email | ✅ Implemented |
| `/customer/reset-password` | POST | Reset password with token | ✅ Implemented |
| `/customer/change-password` | POST | Change password when authenticated | ✅ Implemented |

**Email Service**: `backend/services/emails/email_service.py` has `send_password_reset_email()` method.

### ❌ Frontend Implementation (Missing)

Need to create:
1. **Forgot Password Page** - Public page to request reset
2. **Reset Password Page** - Public page to set new password
3. **Customer Account Settings Page** - Protected page for logged-in users
4. **API Methods** - Frontend API client methods
5. **Login Page Update** - Add "Forgot Password?" link

---

## Implementation Plan

### Phase 1: Frontend Infrastructure

#### 1.1 API Client Methods (`frontend/src/services/api.ts`)

```typescript
// Customer password management methods
async customerForgotPassword(email: string): Promise<{ message: string }> {
  const response = await this.client.post('/customer/forgot-password', { email })
  return response.data
}

async customerResetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const response = await this.client.post('/customer/reset-password', {
    token,
    new_password: newPassword
  })
  return response.data
}

async customerChangePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
  const response = await this.client.post('/customer/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  })
  return response.data
}
```

**Best Practices Applied**:
- ✅ Consistent naming convention (customer prefix)
- ✅ Type-safe with TypeScript
- ✅ Uses existing client instance with interceptors
- ✅ Returns typed responses

---

### Phase 2: Forgot Password Flow

#### 2.1 Forgot Password Page (`frontend/src/pages/Auth/ForgotPasswordPage.tsx`)

**Purpose**: Allow users to request password reset email

**Features**:
- Email input with validation
- Rate limiting feedback (show if email sent successfully without revealing if account exists)
- Link back to login
- Loading states
- Error handling

**UX Best Practices**:
- ✅ **Security**: Always show success message even if email doesn't exist (prevent email enumeration)
- ✅ **Accessibility**: ARIA labels, keyboard navigation
- ✅ **Responsive**: Mobile-first design
- ✅ **Clear CTAs**: Obvious "Send Reset Link" button
- ✅ **Help Text**: Explain what will happen

**Key Code Structure**:
```typescript
const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      await api.customerForgotPassword(email)
      setSubmitted(true)
    } catch (err: any) {
      // Show generic error (don't reveal if email exists)
      setError('An error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Show success state after submission
  if (submitted) {
    return <SuccessMessage />
  }

  return <ForgotPasswordForm />
}
```

**Styling Standards**:
- Semantic CSS variables for colors (e.g., `--color-primary`, `--color-error`)
- Consistent spacing scale (e.g., `--spacing-4`, `--spacing-8`)
- Reusable form components
- Mobile breakpoints at 640px, 768px, 1024px

---

#### 2.2 Reset Password Page (`frontend/src/pages/Auth/ResetPasswordPage.tsx`)

**Purpose**: Allow users to set new password using token from email

**Features**:
- Token extraction from URL query params
- Password input with strength indicator
- Confirm password field
- Password visibility toggle
- Token validation feedback
- Redirect to login after success

**UX Best Practices**:
- ✅ **Password Requirements**: Show clear requirements (8+ chars, letter + number)
- ✅ **Real-time Validation**: Show password strength as user types
- ✅ **Confirmation Match**: Validate passwords match before submit
- ✅ **Token Expiry**: Handle expired tokens gracefully
- ✅ **Success Flow**: Clear next steps after reset

**Key Code Structure**:
```typescript
const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [passwordStrength, setPasswordStrength] = useState<'weak' | 'medium' | 'strong'>('weak')

  // Validate token exists
  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset token')
    }
  }, [token])

  // Calculate password strength
  useEffect(() => {
    setPasswordStrength(calculatePasswordStrength(newPassword))
  }, [newPassword])

  const handleSubmit = async (e: React.FormEvent) => {
    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    try {
      await api.customerResetPassword(token!, newPassword)
      // Show success and redirect
      navigate('/login?reset=success')
    } catch (err) {
      setError('Failed to reset password. Token may be expired.')
    }
  }
}
```

**Password Strength Calculator** (reusable utility):
```typescript
function calculatePasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  let strength = 0
  
  if (password.length >= 8) strength++
  if (password.length >= 12) strength++
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++
  if (/\d/.test(password)) strength++
  if (/[^a-zA-Z0-9]/.test(password)) strength++
  
  if (strength <= 2) return 'weak'
  if (strength <= 4) return 'medium'
  return 'strong'
}
```

---

### Phase 3: Change Password (Customer Portal)

#### 3.1 Customer Account Settings Page (`frontend/src/pages/CustomerPortal/AccountSettingsPage.tsx`)

**Purpose**: Allow logged-in customers to manage their account

**Sections**:
1. **Profile Information** (read-only for now)
   - Email
   - Account created date
   - Subscription status

2. **Change Password**
   - Current password (for verification)
   - New password with strength indicator
   - Confirm new password

**UX Best Practices**:
- ✅ **Verification**: Require current password before change
- ✅ **Inline Validation**: Real-time feedback on password requirements
- ✅ **Success Feedback**: Toast notification on success
- ✅ **Session Management**: Keep user logged in after password change
- ✅ **Error Handling**: Clear messages for wrong current password

**Key Code Structure**:
```typescript
const AccountSettingsPage: React.FC = () => {
  const { user } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const changePasswordMutation = useMutation({
    mutationFn: async () => {
      if (newPassword !== confirmPassword) {
        throw new Error('Passwords do not match')
      }
      return api.customerChangePassword(currentPassword, newPassword)
    },
    onSuccess: () => {
      // Show success toast
      toast.success('Password changed successfully!')
      // Clear form
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to change password'
      toast.error(message)
    }
  })

  return (
    <div className="account-settings">
      <ProfileSection user={user} />
      <ChangePasswordSection
        currentPassword={currentPassword}
        newPassword={newPassword}
        confirmPassword={confirmPassword}
        onCurrentPasswordChange={setCurrentPassword}
        onNewPasswordChange={setNewPassword}
        onConfirmPasswordChange={setConfirmPassword}
        onSubmit={() => changePasswordMutation.mutate()}
        isLoading={changePasswordMutation.isPending}
      />
    </div>
  )
}
```

**Component Modularity**:
- ✅ Separate components for each section
- ✅ Reusable `PasswordInput` component with visibility toggle
- ✅ Shared `PasswordStrengthIndicator` component
- ✅ Custom hooks for form validation

---

### Phase 4: UI/UX Updates

#### 4.1 Login Page Update

Add "Forgot Password?" link below the password field:

```tsx
<div className="login-form">
  <input type="email" /* ... */ />
  <input type="password" /* ... */ />
  
  <div className="forgot-password-link">
    <Link to="/forgot-password" className="link-secondary">
      Forgot your password?
    </Link>
  </div>
  
  <button type="submit">Log In</button>
</div>
```

**Styling**:
```css
.forgot-password-link {
  text-align: right;
  margin-top: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.link-secondary {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-decoration: none;
  transition: color 0.2s ease;
}

.link-secondary:hover {
  color: var(--color-primary);
  text-decoration: underline;
}
```

#### 4.2 Customer Layout Navigation

Add "Account Settings" link to customer portal navigation:

```tsx
<NavLink to="/customer/settings" className={({ isActive }) => isActive ? 'active' : ''}>
  <svg>{ /* Settings icon */ }</svg>
  <span>Account Settings</span>
</NavLink>
```

---

### Phase 5: Routing Configuration

Update `frontend/src/App.tsx`:

```tsx
<Routes>
  {/* Public routes */}
  <Route path="/login" element={<LoginPage />} />
  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
  <Route path="/reset-password" element={<ResetPasswordPage />} />

  {/* Customer Protected routes */}
  <Route path="/customer" element={<ProtectedRoute><CustomerLayout /></ProtectedRoute>}>
    <Route path="sites" element={<MySitesPage />} />
    <Route path="domains" element={<DomainsPage />} />
    <Route path="tickets" element={<TicketsPage />} />
    <Route path="settings" element={<AccountSettingsPage />} /> {/* NEW */}
  </Route>
</Routes>
```

---

## Best Practices Implementation

### 1. **Security Best Practices**

✅ **Password Requirements**:
- Minimum 8 characters
- At least one letter and one number
- Validated on both frontend and backend

✅ **Token Security**:
- Reset tokens expire after 1 hour (backend)
- Tokens are single-use (invalidated after reset)
- URL tokens never logged or cached

✅ **Rate Limiting**:
- Backend enforces rate limits on password reset requests
- Frontend prevents rapid form submissions

✅ **No Information Disclosure**:
- Forgot password always shows success (doesn't reveal if email exists)
- Error messages don't reveal sensitive information

### 2. **Code Modularity**

✅ **Reusable Components**:
```
frontend/src/components/
  - PasswordInput/
    - PasswordInput.tsx
    - PasswordInput.css
  - PasswordStrengthIndicator/
    - PasswordStrengthIndicator.tsx
    - PasswordStrengthIndicator.css
  - FormCard/
    - FormCard.tsx
    - FormCard.css
```

✅ **Custom Hooks**:
```typescript
// usePasswordValidation.ts
export const usePasswordValidation = (password: string) => {
  const [validation, setValidation] = useState({
    hasMinLength: false,
    hasLetter: false,
    hasNumber: false,
    isValid: false
  })

  useEffect(() => {
    setValidation({
      hasMinLength: password.length >= 8,
      hasLetter: /[a-zA-Z]/.test(password),
      hasNumber: /\d/.test(password),
      isValid: password.length >= 8 && /[a-zA-Z]/.test(password) && /\d/.test(password)
    })
  }, [password])

  return validation
}
```

### 3. **Semantic CSS Variables**

```css
:root {
  /* Colors */
  --color-primary: #6366f1;
  --color-primary-hover: #4f46e5;
  --color-success: #10b981;
  --color-error: #ef4444;
  --color-warning: #f59e0b;
  
  /* Text */
  --color-text-primary: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-tertiary: #9ca3af;
  
  /* Backgrounds */
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f9fafb;
  --color-bg-tertiary: #f3f4f6;
  
  /* Spacing Scale */
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-6: 1.5rem;
  --spacing-8: 2rem;
  --spacing-12: 3rem;
  
  /* Typography */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  
  /* Border Radius */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  
  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;
}
```

### 4. **Readable Functions**

✅ **Single Responsibility**:
```typescript
// Good: Each function does one thing
const validatePasswordMatch = (password: string, confirmPassword: string): boolean => {
  return password === confirmPassword
}

const validatePasswordStrength = (password: string): boolean => {
  return password.length >= 8 && /[a-zA-Z]/.test(password) && /\d/.test(password)
}

const validateForm = (password: string, confirmPassword: string): string | null => {
  if (!validatePasswordStrength(password)) {
    return 'Password must be at least 8 characters with letters and numbers'
  }
  if (!validatePasswordMatch(password, confirmPassword)) {
    return 'Passwords do not match'
  }
  return null
}
```

✅ **Clear Naming**:
```typescript
// Bad: Unclear abbreviations
const handlePwdChg = () => { /* ... */ }

// Good: Descriptive names
const handlePasswordChange = () => { /* ... */ }
const validatePasswordRequirements = () => { /* ... */ }
const displayPasswordStrengthIndicator = () => { /* ... */ }
```

### 5. **Error Handling**

✅ **Graceful Degradation**:
```typescript
const handleResetPassword = async () => {
  try {
    await api.customerResetPassword(token, newPassword)
    navigate('/login?reset=success')
  } catch (error: any) {
    // Check for specific error types
    if (error.response?.status === 400) {
      setError('Invalid or expired reset link. Please request a new one.')
    } else if (error.response?.status === 422) {
      setError('Password does not meet requirements.')
    } else {
      setError('An unexpected error occurred. Please try again.')
    }
    
    // Log error for debugging (never log sensitive data)
    console.error('Password reset failed:', error.message)
  }
}
```

### 6. **Accessibility (WCAG 2.1 AA)**

✅ **Form Accessibility**:
```tsx
<label htmlFor="new-password" className="form-label">
  New Password
  <span className="required-indicator" aria-label="required">*</span>
</label>
<input
  id="new-password"
  type={showPassword ? 'text' : 'password'}
  value={newPassword}
  onChange={(e) => setNewPassword(e.target.value)}
  aria-required="true"
  aria-invalid={!!passwordError}
  aria-describedby="password-requirements password-error"
  className={`form-input ${passwordError ? 'input-error' : ''}`}
/>
<div id="password-requirements" className="form-hint">
  At least 8 characters with letters and numbers
</div>
{passwordError && (
  <div id="password-error" className="form-error" role="alert">
    {passwordError}
  </div>
)}
```

✅ **Keyboard Navigation**:
- All interactive elements focusable
- Logical tab order
- Enter key submits forms
- Escape key closes modals

✅ **Screen Reader Support**:
- Proper ARIA labels
- Status announcements for success/error
- Live regions for dynamic content

---

## File Structure

```
frontend/src/
├── pages/
│   ├── Auth/
│   │   ├── LoginPage.tsx ✏️ (update)
│   │   ├── LoginPage.css ✏️ (update)
│   │   ├── ForgotPasswordPage.tsx ➕ (new)
│   │   ├── ForgotPasswordPage.css ➕ (new)
│   │   ├── ResetPasswordPage.tsx ➕ (new)
│   │   └── ResetPasswordPage.css ➕ (new)
│   └── CustomerPortal/
│       ├── AccountSettingsPage.tsx ➕ (new)
│       └── AccountSettingsPage.css ➕ (new)
├── components/
│   ├── PasswordInput/
│   │   ├── PasswordInput.tsx ➕ (new)
│   │   └── PasswordInput.css ➕ (new)
│   └── PasswordStrengthIndicator/
│       ├── PasswordStrengthIndicator.tsx ➕ (new)
│       └── PasswordStrengthIndicator.css ➕ (new)
├── hooks/
│   └── usePasswordValidation.ts ➕ (new)
├── services/
│   └── api.ts ✏️ (update)
├── layouts/
│   └── CustomerLayout.tsx ✏️ (update)
└── App.tsx ✏️ (update routes)
```

---

## Testing Strategy

### Unit Tests

✅ **Password Validation Logic**:
```typescript
describe('validatePasswordStrength', () => {
  it('rejects passwords shorter than 8 characters', () => {
    expect(validatePasswordStrength('abc123')).toBe(false)
  })

  it('rejects passwords without letters', () => {
    expect(validatePasswordStrength('12345678')).toBe(false)
  })

  it('rejects passwords without numbers', () => {
    expect(validatePasswordStrength('abcdefgh')).toBe(false)
  })

  it('accepts valid passwords', () => {
    expect(validatePasswordStrength('password123')).toBe(true)
  })
})
```

### Integration Tests

✅ **Complete Password Reset Flow**:
1. Request password reset
2. Verify email sent (mock)
3. Use reset token
4. Login with new password

### Manual Testing Checklist

- [ ] Forgot password page loads
- [ ] Email validation works
- [ ] Success message displays after submission
- [ ] Reset password page validates token
- [ ] Password strength indicator updates correctly
- [ ] Passwords must match to submit
- [ ] Successful reset redirects to login
- [ ] Change password requires current password
- [ ] Invalid current password shows error
- [ ] Successful password change shows confirmation
- [ ] Mobile responsive layout works
- [ ] Keyboard navigation functions properly
- [ ] Screen reader announces status changes

---

## Email Templates (Backend)

Verify these templates exist and are professional:

### Password Reset Email (`backend/services/emails/templates.py`)

Should include:
- Clear subject line: "Reset Your Password"
- Personalized greeting with customer name
- Explanation of why they're receiving this
- Prominent "Reset Password" button/link
- Link expiration time (1 hour)
- Security note: "If you didn't request this, ignore this email"
- Support contact information

**Example Structure**:
```html
<div style="max-width: 600px; margin: 0 auto; font-family: sans-serif;">
  <h1>Reset Your Password</h1>
  <p>Hi {{customer_name}},</p>
  <p>We received a request to reset your password. Click the button below to choose a new password:</p>
  <a href="{{reset_url}}" style="...">Reset My Password</a>
  <p style="color: #666;">This link will expire in 1 hour.</p>
  <hr />
  <p style="font-size: 14px; color: #999;">
    If you didn't request this, you can safely ignore this email. 
    Your password will remain unchanged.
  </p>
</div>
```

---

## Success Metrics

### User Experience
- ✅ Password reset flow completes in < 3 minutes
- ✅ < 5% error rate on password changes
- ✅ Mobile responsive on all screen sizes

### Security
- ✅ No password exposure in logs or URLs
- ✅ Token expiry enforced
- ✅ Rate limiting prevents abuse

### Code Quality
- ✅ 100% TypeScript type coverage
- ✅ All components have proper CSS modules
- ✅ Semantic HTML with ARIA attributes
- ✅ Reusable components for common patterns

---

## Implementation Timeline

### Sprint 1 (This Session)
1. Create reusable components (PasswordInput, PasswordStrengthIndicator)
2. Add API methods to `api.ts`
3. Create ForgotPasswordPage
4. Create ResetPasswordPage
5. Update LoginPage with forgot password link

### Sprint 2 (Next)
1. Create AccountSettingsPage for customer portal
2. Update CustomerLayout navigation
3. Add routing configuration
4. Test complete flow end-to-end

---

## Summary

This implementation provides a complete, secure, and user-friendly password management system following industry best practices:

✅ **Security First**: Token-based resets, password requirements, rate limiting
✅ **Excellent UX**: Clear flows, helpful feedback, mobile-responsive
✅ **Maintainable Code**: Modular components, semantic CSS, TypeScript
✅ **Accessible**: WCAG 2.1 AA compliant
✅ **Production Ready**: Error handling, loading states, validation

The backend is already complete, so we only need to build the frontend UI components to complete this feature!
