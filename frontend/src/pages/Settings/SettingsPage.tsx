/**
 * Settings Page
 * 
 * Tabbed interface for:
 * - Account Settings (password change, profile)
 * - AI Models (configure LLM and image generation)
 * - Prompt Settings (AI agent configuration)
 */
import { useState } from 'react'
import { Card } from '@/components/ui'
import { User, Key, Bot, MessageSquare, Link2, Bell, Zap } from 'lucide-react'
import { AccountSettings } from './AccountSettings'
import { AISettingsTab } from './AISettingsTab'
import { PromptsSettings } from './PromptsSettings'
import { MessagingSettings } from './MessagingSettings'
import { ShortenerSettings } from './ShortenerSettings'
import { NotificationSettings } from './NotificationSettings'
import { AutopilotSettings } from './AutopilotSettings'

type SettingsTab = 'account' | 'ai' | 'prompts' | 'messaging' | 'shortener' | 'notifications' | 'autopilot'

export const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('account')

  const tabs = [
    {
      id: 'account' as SettingsTab,
      label: 'Account Settings',
      icon: User,
      description: 'Manage your account and security',
    },
    {
      id: 'autopilot' as SettingsTab,
      label: 'Autopilot',
      icon: Zap,
      description: 'Enable fully automatic pipeline and set lead targets',
    },
    {
      id: 'ai' as SettingsTab,
      label: 'AI Models',
      icon: Bot,
      description: 'Configure AI providers and models',
    },
    {
      id: 'messaging' as SettingsTab,
      label: 'Messaging',
      icon: MessageSquare,
      description: 'Configure SMS templates (Friendly, Professional, Urgent)',
    },
    {
      id: 'prompts' as SettingsTab,
      label: 'Prompt Settings',
      icon: Key,
      description: 'Configure AI agent prompts',
    },
    {
      id: 'shortener' as SettingsTab,
      label: 'URL Shortener',
      icon: Link2,
      description: 'Configure short URLs for SMS campaigns',
    },
    {
      id: 'notifications' as SettingsTab,
      label: 'Notifications',
      icon: Bell,
      description: 'Configure support ticket email alerts',
    },
  ]

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Settings</h1>
          <p className="text-text-secondary">Manage your account and system configuration</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-container mb-6">
        <div className="tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab ${activeTab === tab.id ? 'tab-active' : ''} flex items-center gap-2 px-4 py-3`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="page-content">
        {activeTab === 'account' && <AccountSettings />}
        {activeTab === 'autopilot' && <AutopilotSettings />}
        {activeTab === 'ai' && <AISettingsTab />}
        {activeTab === 'messaging' && <MessagingSettings />}
        {activeTab === 'prompts' && <PromptsSettings />}
        {activeTab === 'shortener' && <ShortenerSettings />}
        {activeTab === 'notifications' && <NotificationSettings />}
      </div>
    </div>
  )
}
