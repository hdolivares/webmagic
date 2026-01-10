# WebMagic: Admin Dashboard

## Next.js Frontend Specifications

This document details the admin dashboard design, component library, and theming system.

---

## 🎨 Design System

### CSS Variables (Semantic Theming)

```css
/* styles/variables.css */

:root {
  /* === COLORS === */
  
  /* Brand Colors */
  --color-brand-primary: #6366f1;      /* Indigo */
  --color-brand-secondary: #8b5cf6;    /* Purple */
  --color-brand-accent: #f59e0b;       /* Amber */
  
  /* Semantic Colors */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;
  
  /* Surface Colors (Light Mode) */
  --color-background: #ffffff;
  --color-surface: #f8fafc;
  --color-surface-elevated: #ffffff;
  --color-border: #e2e8f0;
  --color-border-subtle: #f1f5f9;
  
  /* Text Colors (Light Mode) */
  --color-text-primary: #0f172a;
  --color-text-secondary: #475569;
  --color-text-tertiary: #94a3b8;
  --color-text-inverse: #ffffff;
  
  /* === TYPOGRAPHY === */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  --text-xs: 0.75rem;      /* 12px */
  --text-sm: 0.875rem;     /* 14px */
  --text-base: 1rem;       /* 16px */
  --text-lg: 1.125rem;     /* 18px */
  --text-xl: 1.25rem;      /* 20px */
  --text-2xl: 1.5rem;      /* 24px */
  --text-3xl: 1.875rem;    /* 30px */
  
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  
  /* === SPACING === */
  --space-1: 0.25rem;      /* 4px */
  --space-2: 0.5rem;       /* 8px */
  --space-3: 0.75rem;      /* 12px */
  --space-4: 1rem;         /* 16px */
  --space-5: 1.25rem;      /* 20px */
  --space-6: 1.5rem;       /* 24px */
  --space-8: 2rem;         /* 32px */
  --space-10: 2.5rem;      /* 40px */
  --space-12: 3rem;        /* 48px */
  
  /* === BORDERS === */
  --radius-sm: 0.25rem;    /* 4px */
  --radius-md: 0.375rem;   /* 6px */
  --radius-lg: 0.5rem;     /* 8px */
  --radius-xl: 0.75rem;    /* 12px */
  --radius-full: 9999px;
  
  /* === SHADOWS === */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
  
  /* === TRANSITIONS === */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;
  
  /* === LAYOUT === */
  --sidebar-width: 280px;
  --sidebar-collapsed-width: 72px;
  --header-height: 64px;
}

/* === DARK MODE === */
[data-theme="dark"] {
  --color-background: #0f172a;
  --color-surface: #1e293b;
  --color-surface-elevated: #334155;
  --color-border: #334155;
  --color-border-subtle: #1e293b;
  
  --color-text-primary: #f8fafc;
  --color-text-secondary: #cbd5e1;
  --color-text-tertiary: #64748b;
  
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4);
}
```

### Semantic Component Classes

```css
/* styles/components.css */

/* === CARDS === */
.card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

/* === BUTTONS === */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
}

.btn-primary:hover {
  background: color-mix(in srgb, var(--color-brand-primary), black 10%);
}

.btn-secondary {
  background: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-ghost {
  background: transparent;
  color: var(--color-text-secondary);
}

.btn-ghost:hover {
  background: var(--color-surface);
}

.btn-danger {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

/* === STATUS BADGES === */
.badge {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-full);
}

.badge-success {
  background: color-mix(in srgb, var(--color-success), transparent 85%);
  color: var(--color-success);
}

.badge-warning {
  background: color-mix(in srgb, var(--color-warning), transparent 85%);
  color: var(--color-warning);
}

.badge-error {
  background: color-mix(in srgb, var(--color-error), transparent 85%);
  color: var(--color-error);
}

.badge-info {
  background: color-mix(in srgb, var(--color-info), transparent 85%);
  color: var(--color-info);
}

/* === INPUTS === */
.input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  transition: border-color var(--transition-fast);
}

.input:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-brand-primary), transparent 85%);
}

.input-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

/* === TABLES === */
.table-container {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-subtle);
}

.table tr:last-child td {
  border-bottom: none;
}

.table tr:hover {
  background: var(--color-surface);
}
```

---

## 📐 Layout Structure

### Dashboard Shell

```tsx
// src/app/(dashboard)/layout.tsx

import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';

export default function DashboardLayout({
  children
}: {
  children: React.ReactNode
}) {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <div className="dashboard-main">
        <Header />
        <main className="dashboard-content">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Sidebar Component

```tsx
// src/components/layout/sidebar.tsx

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Building2, 
  Globe, 
  Mail, 
  Users,
  Map,
  BarChart3,
  Settings,
  Sparkles
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Businesses', href: '/businesses', icon: Building2 },
  { name: 'Sites', href: '/sites', icon: Globe },
  { name: 'Campaigns', href: '/campaigns', icon: Mail },
  { name: 'Customers', href: '/customers', icon: Users },
  { name: 'Coverage', href: '/coverage', icon: Map },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { divider: true },
  { name: 'Prompts', href: '/settings/prompts', icon: Sparkles },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">✨ WebMagic</span>
      </div>
      
      <nav className="sidebar-nav">
        {navigation.map((item, index) => {
          if (item.divider) {
            return <div key={index} className="sidebar-divider" />;
          }
          
          const isActive = pathname === item.href || 
                          pathname.startsWith(item.href + '/');
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`sidebar-link ${isActive ? 'active' : ''}`}
            >
              <item.icon className="sidebar-icon" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="sidebar-footer">
        <div className="sidebar-stats">
          <span className="stat-value">127</span>
          <span className="stat-label">Sites Generated</span>
        </div>
      </div>
    </aside>
  );
}
```

---

## 📄 Key Pages

### Dashboard Home

```tsx
// src/app/page.tsx

import { StatCard } from '@/components/data-display/stat-card';
import { RecentActivity } from '@/components/data-display/recent-activity';
import { ConversionChart } from '@/components/charts/conversion-chart';

export default async function DashboardPage() {
  // Fetch stats from API
  const stats = await fetchDashboardStats();
  
  return (
    <div className="page-dashboard">
      <h1 className="page-title">Dashboard</h1>
      
      {/* Stats Grid */}
      <div className="stats-grid">
        <StatCard
          title="Leads Today"
          value={stats.leadsToday}
          change={stats.leadsChange}
          icon="users"
        />
        <StatCard
          title="Sites Generated"
          value={stats.sitesGenerated}
          change={stats.sitesChange}
          icon="globe"
        />
        <StatCard
          title="Emails Sent"
          value={stats.emailsSent}
          change={stats.emailsChange}
          icon="mail"
        />
        <StatCard
          title="Conversions"
          value={stats.conversions}
          change={stats.conversionsChange}
          icon="dollar"
          highlight
        />
      </div>
      
      {/* Charts */}
      <div className="charts-grid">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Conversion Funnel</h2>
          </div>
          <ConversionChart data={stats.funnelData} />
        </div>
        
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Recent Activity</h2>
          </div>
          <RecentActivity items={stats.recentActivity} />
        </div>
      </div>
    </div>
  );
}
```

### Prompt Settings Page

```tsx
// src/app/(dashboard)/settings/prompts/page.tsx

import { AgentCard } from '@/components/forms/agent-card';

const agents = [
  {
    id: 'analyst',
    name: 'The Analyst',
    description: 'Extracts brand DNA and sales hooks from business data',
    sections: ['analysis_guidelines'],
    icon: '🔍'
  },
  {
    id: 'concept',
    name: 'The Concept',
    description: 'Invents distinctive brand personalities',
    sections: ['concept_types', 'concept_rules'],
    icon: '💡'
  },
  {
    id: 'director',
    name: 'The Art Director',
    description: 'Creates detailed design briefs',
    sections: ['frontend_aesthetics', 'vibe_list', 'typography_rules', 'banned_patterns'],
    icon: '🎨'
  },
  {
    id: 'architect',
    name: 'The Architect',
    description: 'Writes the HTML/CSS/JS code',
    sections: ['technical_requirements', 'section_templates'],
    icon: '🏗️'
  },
  {
    id: 'email_composer',
    name: 'Email Composer',
    description: 'Creates personalized cold emails',
    sections: ['email_template', 'subject_line_rules'],
    icon: '✉️'
  }
];

export default function PromptsPage() {
  return (
    <div className="page-prompts">
      <div className="page-header">
        <h1 className="page-title">Prompt Settings</h1>
        <p className="page-description">
          Customize the AI agents that power WebMagic. 
          Changes take effect immediately for new generations.
        </p>
      </div>
      
      <div className="agents-grid">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
```

### Agent Edit Page

```tsx
// src/app/(dashboard)/settings/prompts/[agentId]/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { PromptEditor } from '@/components/forms/prompt-editor';
import { usePromptSections } from '@/hooks/use-prompts';

export default function AgentEditPage() {
  const { agentId } = useParams();
  const { sections, isLoading, updateSection } = usePromptSections(agentId);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  
  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }
  
  return (
    <div className="page-agent-edit">
      <div className="page-header">
        <h1 className="page-title">
          {getAgentName(agentId)} Settings
        </h1>
        <p className="page-description">
          Edit the prompt sections for this agent.
          Master instructions cannot be changed here.
        </p>
      </div>
      
      <div className="sections-list">
        {sections.map((section) => (
          <div 
            key={section.id}
            className={`section-card ${activeSection === section.id ? 'active' : ''}`}
          >
            <div 
              className="section-header"
              onClick={() => setActiveSection(
                activeSection === section.id ? null : section.id
              )}
            >
              <div>
                <h3 className="section-name">{section.section_name}</h3>
                <p className="section-description">{section.description}</p>
              </div>
              <div className="section-meta">
                <span className="badge badge-info">v{section.version}</span>
                <span className="section-toggle">
                  {activeSection === section.id ? '▼' : '▶'}
                </span>
              </div>
            </div>
            
            {activeSection === section.id && (
              <div className="section-content">
                <PromptEditor
                  value={section.content}
                  onChange={(content) => updateSection(section.id, content)}
                />
                <div className="section-actions">
                  <button className="btn btn-primary">
                    Save Changes
                  </button>
                  <button className="btn btn-ghost">
                    Test
                  </button>
                  <button className="btn btn-ghost">
                    View History
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🧩 Key Components

### Stat Card

```tsx
// src/components/data-display/stat-card.tsx

interface StatCardProps {
  title: string;
  value: number | string;
  change?: number;
  icon: string;
  highlight?: boolean;
}

export function StatCard({ title, value, change, icon, highlight }: StatCardProps) {
  const isPositive = change && change > 0;
  const isNegative = change && change < 0;
  
  return (
    <div className={`stat-card ${highlight ? 'stat-card-highlight' : ''}`}>
      <div className="stat-card-header">
        <span className="stat-card-icon">{getIcon(icon)}</span>
        <span className="stat-card-title">{title}</span>
      </div>
      <div className="stat-card-value">{formatNumber(value)}</div>
      {change !== undefined && (
        <div className={`stat-card-change ${isPositive ? 'positive' : ''} ${isNegative ? 'negative' : ''}`}>
          {isPositive && '↑'}
          {isNegative && '↓'}
          {Math.abs(change)}% vs last week
        </div>
      )}
    </div>
  );
}
```

### Prompt Editor

```tsx
// src/components/forms/prompt-editor.tsx

'use client';

import { useState, useRef } from 'react';

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function PromptEditor({ value, onChange, placeholder }: PromptEditorProps) {
  const [localValue, setLocalValue] = useState(value);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Auto-resize textarea
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalValue(e.target.value);
    
    // Resize
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    }
  };
  
  const handleBlur = () => {
    if (localValue !== value) {
      onChange(localValue);
    }
  };
  
  return (
    <div className="prompt-editor">
      <div className="prompt-editor-toolbar">
        <button className="toolbar-btn" title="Insert variable">
          {'{{ }}'}
        </button>
        <button className="toolbar-btn" title="Format">
          Format
        </button>
      </div>
      <textarea
        ref={textareaRef}
        className="prompt-editor-textarea"
        value={localValue}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        spellCheck={false}
      />
      <div className="prompt-editor-footer">
        <span className="char-count">
          {localValue.length} characters
        </span>
      </div>
    </div>
  );
}
```

### Site Preview

```tsx
// src/components/data-display/site-preview.tsx

'use client';

import { useState } from 'react';

interface SitePreviewProps {
  subdomain: string;
  screenshotDesktop?: string;
  screenshotMobile?: string;
}

export function SitePreview({ subdomain, screenshotDesktop, screenshotMobile }: SitePreviewProps) {
  const [view, setView] = useState<'desktop' | 'mobile' | 'live'>('desktop');
  
  const liveUrl = `https://${subdomain}.webmagic.com`;
  
  return (
    <div className="site-preview">
      <div className="preview-toolbar">
        <div className="preview-tabs">
          <button 
            className={`preview-tab ${view === 'desktop' ? 'active' : ''}`}
            onClick={() => setView('desktop')}
          >
            Desktop
          </button>
          <button 
            className={`preview-tab ${view === 'mobile' ? 'active' : ''}`}
            onClick={() => setView('mobile')}
          >
            Mobile
          </button>
          <button 
            className={`preview-tab ${view === 'live' ? 'active' : ''}`}
            onClick={() => setView('live')}
          >
            Live
          </button>
        </div>
        <a 
          href={liveUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="btn btn-secondary"
        >
          Open in New Tab ↗
        </a>
      </div>
      
      <div className={`preview-frame preview-${view}`}>
        {view === 'live' ? (
          <iframe 
            src={liveUrl}
            className="preview-iframe"
            sandbox="allow-scripts allow-same-origin"
          />
        ) : (
          <img 
            src={view === 'desktop' ? screenshotDesktop : screenshotMobile}
            alt={`${view} preview`}
            className="preview-screenshot"
          />
        )}
      </div>
    </div>
  );
}
```

---

## 🔌 API Client

```typescript
// src/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private token: string | null = null;
  
  setToken(token: string) {
    this.token = token;
  }
  
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'API request failed');
    }
    
    return response.json();
  }
  
  // Businesses
  async getBusinesses(params?: Record<string, string>) {
    const query = params ? '?' + new URLSearchParams(params) : '';
    return this.request(`/businesses${query}`);
  }
  
  async getBusiness(id: string) {
    return this.request(`/businesses/${id}`);
  }
  
  // Sites
  async getSites(params?: Record<string, string>) {
    const query = params ? '?' + new URLSearchParams(params) : '';
    return this.request(`/sites${query}`);
  }
  
  async getSite(id: string) {
    return this.request(`/sites/${id}`);
  }
  
  // Prompts
  async getAgentSections(agentName: string) {
    return this.request(`/settings/prompts/agents/${agentName}`);
  }
  
  async updateSection(agentName: string, sectionName: string, content: string) {
    return this.request(`/settings/prompts/agents/${agentName}/${sectionName}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  }
  
  // Analytics
  async getDashboardStats() {
    return this.request('/analytics/dashboard');
  }
}

export const api = new ApiClient();
```

---

## 🎯 React Hooks

```typescript
// src/hooks/use-prompts.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function usePromptSections(agentId: string) {
  const queryClient = useQueryClient();
  
  const { data: sections, isLoading } = useQuery({
    queryKey: ['prompts', agentId],
    queryFn: () => api.getAgentSections(agentId),
  });
  
  const mutation = useMutation({
    mutationFn: ({ sectionName, content }: { sectionName: string; content: string }) =>
      api.updateSection(agentId, sectionName, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts', agentId] });
    },
  });
  
  const updateSection = (sectionName: string, content: string) => {
    mutation.mutate({ sectionName, content });
  };
  
  return {
    sections: sections || [],
    isLoading,
    updateSection,
    isUpdating: mutation.isPending,
  };
}
```

---

## 📦 Dependencies

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "lucide-react": "^0.300.0",
    "recharts": "^2.10.0",
    "clsx": "^2.0.0",
    "date-fns": "^3.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "@types/react": "^18.2.0",
    "@types/node": "^20.0.0"
  }
}
```
