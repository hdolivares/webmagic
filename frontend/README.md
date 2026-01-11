# WebMagic Admin Frontend

Modern, responsive admin dashboard for WebMagic built with React, TypeScript, and Tailwind CSS.

## 🎨 Features

- **Semantic CSS System** - CSS variables for easy theming
- **Light/Dark Mode** - Built-in theme switching
- **Type-Safe** - Full TypeScript coverage
- **Responsive** - Mobile-first design
- **Modular** - Clean component architecture

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file:

```
VITE_API_URL=/api/v1
```

## 📁 Project Structure

```
src/
├── components/        # Reusable UI components
│   ├── ui/           # Base UI components (Button, Card, Badge)
│   └── layout/       # Layout components (Sidebar, Header)
├── pages/            # Page components
│   ├── Auth/         # Login page
│   ├── Dashboard/    # Analytics dashboard
│   ├── Businesses/   # Business management
│   ├── Sites/        # Site gallery
│   ├── Campaigns/    # Email campaigns
│   ├── Customers/    # Customer portal
│   └── Settings/     # Prompt settings editor
├── hooks/            # Custom React hooks
│   ├── useAuth.ts    # Authentication state
│   └── useTheme.ts   # Theme management
├── services/         # API clients
│   └── api.ts        # Backend API client
├── types/            # TypeScript definitions
│   └── index.ts      # Shared types
└── styles/           # Global styles
    ├── theme.css     # CSS variables & theme
    └── global.css    # Semantic component classes
```

## 🎨 Semantic CSS System

All styles use semantic naming and CSS variables:

### Colors
- `primary` - Brand color (purple/indigo)
- `secondary` - Supporting color (slate)
- `accent` - Highlight color (cyan)
- `success`, `warning`, `error`, `info` - Status colors
- `background`, `surface`, `border`, `text` - Layout colors

### Components
- `.btn-primary`, `.btn-secondary`, etc. - Buttons
- `.badge-success`, `.badge-error`, etc. - Badges
- `.card`, `.card-header`, `.card-body` - Cards
- `.input`, `.select`, `.textarea` - Forms
- `.nav-link`, `.nav-link-active` - Navigation
- `.alert-success`, `.alert-error` - Alerts

### Usage Example

```tsx
import { Button, Card, Badge } from '@/components/ui'

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <Badge variant="success">Active</Badge>
  </CardHeader>
  <CardBody>
    <Button variant="primary">Click Me</Button>
  </CardBody>
</Card>
```

## 🌓 Theme System

Theme automatically switches between light and dark modes:

```tsx
import { useTheme } from '@/hooks/useTheme'

const { theme, toggleTheme } = useTheme()
```

All colors adapt automatically via CSS variables.

## 🔐 Authentication

Uses JWT tokens stored in localStorage:

```tsx
import { useAuth } from '@/hooks/useAuth'

const { user, login, logout } = useAuth()
```

## 📊 Data Fetching

Uses React Query for server state:

```tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'

const { data, isLoading } = useQuery({
  queryKey: ['businesses'],
  queryFn: () => api.getBusinesses(),
})
```

## 🛠️ Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Utility-first CSS
- **React Router** - Routing
- **React Query** - Server state
- **Zustand** - Client state
- **Axios** - HTTP client
- **Lucide React** - Icons

## 📝 Best Practices

- **Modular Components** - Each component has single responsibility
- **Semantic Naming** - CSS classes describe purpose, not appearance
- **Type Safety** - Full TypeScript coverage with strict mode
- **Accessibility** - ARIA labels and keyboard navigation
- **Performance** - Code splitting and lazy loading
- **Responsive** - Mobile-first approach

## 🎯 Pages

### Dashboard
Analytics overview with key metrics and quick actions.

### Businesses
Manage scraped business leads with filtering and status updates.

### Sites
Gallery of AI-generated websites with preview links.

### Campaigns
Email campaign tracking with open/click rates.

### Customers
Customer portal with payment history and subscriptions.

### Settings
LLM prompt editor for customizing AI agent behavior.

---

Built with ❤️ for WebMagic
