# Customer Portal Setup Guide

## Overview
WebMagic has **two separate authentication systems**:
1. **Admin Portal** - For WebMagic staff/administrators
2. **Customer Portal** - For clients who purchased websites

---

## Authentication Endpoints

### Admin Login (Current Setup)
- **URL**: `https://web.lavish.solutions/login`
- **API Endpoint**: `/api/v1/auth/login`
- **User Type**: `AdminUser`
- **Access**: Full dashboard, all features

### Customer Login (Needs Frontend Implementation)
- **API Endpoint**: `/api/v1/customer/login`
- **User Type**: `CustomerUser`
- **Access**: Limited to:
  - Custom Domains management
  - Support Tickets (My Tickets)

---

## Backend Status ✅

The customer authentication backend is **fully implemented**:

### Available Customer API Endpoints
```
POST   /api/v1/customer/register          - Register new customer
POST   /api/v1/customer/login             - Customer login
POST   /api/v1/customer/verify-email      - Verify email
POST   /api/v1/customer/resend-verification - Resend verification
POST   /api/v1/customer/forgot-password   - Request password reset
POST   /api/v1/customer/reset-password    - Reset password
POST   /api/v1/customer/change-password   - Change password
GET    /api/v1/customer/profile           - Get customer profile
PATCH  /api/v1/customer/profile           - Update customer profile
```

### Customer Features (Backend Ready)
- ✅ JWT token-based authentication
- ✅ Email verification system
- ✅ Password reset flow
- ✅ Profile management
- ✅ Custom domain management (Phase 5)
- ✅ Support ticket system (Phase 6)

---

## Frontend Status ⚠️

### What's Implemented
- ✅ `CustomerLayout` component with restricted navigation
- ✅ Custom domain management pages
- ✅ Support ticket pages (list, detail, create)
- ✅ API client methods for customer authentication

### What's Missing (To-Do)
- ❌ Customer login page UI
- ❌ Customer registration page UI
- ❌ Customer-specific routing
- ❌ Separate customer portal domain/subdomain (optional)

---

## Next Steps: Implementing Customer Portal UI

### Option 1: Separate Domain/Subdomain (Recommended)
Set up a separate customer portal:
- **Domain**: `portal.lavish.solutions` or `customers.lavish.solutions`
- **Benefits**: Clear separation, better UX, easier branding

### Option 2: Same Domain, Different Route
Add customer routes to existing domain:
- **Route**: `https://web.lavish.solutions/customer/login`
- **Benefits**: Simpler deployment, single domain

---

## Implementation Checklist

### Frontend Components Needed
1. **Customer Login Page** (`/customer/login`)
   - Email/password form
   - "Forgot password?" link
   - Link to registration (if needed)

2. **Customer Registration Page** (`/customer/register`)
   - Full name, email, phone, password
   - Terms acceptance
   - Email verification flow

3. **Customer Dashboard** (`/customer/dashboard`)
   - Welcome message
   - Quick links to domains & tickets
   - Site information display

4. **Email Verification Page** (`/customer/verify-email`)
   - Token verification
   - Success/error states

5. **Password Reset Pages**
   - Forgot password form
   - Reset password form with token

### Routing Setup
```typescript
// Example routes
/customer/login           → CustomerLoginPage
/customer/register        → CustomerRegisterPage
/customer/dashboard       → CustomerDashboard
/customer/domains         → DomainsPage (already exists)
/customer/tickets         → TicketsPage (already exists)
/customer/verify-email    → EmailVerificationPage
/customer/forgot-password → ForgotPasswordPage
/customer/reset-password  → ResetPasswordPage
```

---

## Purchase Flow Integration

When a customer purchases a website:
1. **Order completion** triggers customer account creation
2. **Welcome email** sent with login credentials
3. **Customer logs in** via customer portal
4. **Can manage**:
   - Connect custom domain
   - Submit support tickets
   - View their purchased website(s)

---

## Security Notes

- Customers can **only** see/manage their own purchased websites
- Customer authentication uses **separate JWT tokens**
- Customer sessions are **independent** from admin sessions
- Customer roles/permissions are **restricted by default**

---

## Current Issue Fixed ✅

**Settings Page 404 Errors**: The system router was missing the `/system` prefix, causing 404 errors when accessing AI configuration endpoints. This has been fixed:
- Before: `/api/v1/ai-config` (404)
- After: `/api/v1/system/ai-config` (works)

**Status**: Deployed and working ✅

