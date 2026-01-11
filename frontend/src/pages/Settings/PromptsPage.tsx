/**
 * Prompt Settings Page
 * 
 * Allows configuration of AI agent prompts for the creative pipeline.
 */
import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Wrench, Lightbulb, Palette, Code, Mail } from 'lucide-react'

interface PromptTemplate {
  id: string
  agent_name: string
  description: string
  sections_count: number
}

interface PromptSetting {
  id: string
  template_id: string
  section_name: string
  content: string
  description: string | null
  version: number
}

const AGENT_ICONS: Record<string, any> = {
  analyst: Wrench,
  concept: Lightbulb,
  art_director: Palette,
  architect: Code,
  email_composer: Mail,
}

export function PromptsPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [settings, setSettings] = useState<PromptSetting[]>([])
  const [selectedSetting, setSelectedSetting] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadTemplates()
  }, [])

  useEffect(() => {
    if (selectedTemplate) {
      loadSettings(selectedTemplate)
    }
  }, [selectedTemplate])

  const loadTemplates = async () => {
    try {
      const response = await fetch('/api/v1/settings/templates')
      const data = await response.json()
      setTemplates(data)
      if (data.length > 0) {
        setSelectedTemplate(data[0].id)
      }
      setLoading(false)
    } catch (error) {
      console.error('Failed to load templates:', error)
      setLoading(false)
    }
  }

  const loadSettings = async (templateId: string) => {
    try {
      const response = await fetch(`/api/v1/settings/templates/${templateId}/settings`)
      const data = await response.json()
      setSettings(data)
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const handleSettingClick = (setting: PromptSetting) => {
    setSelectedSetting(setting.id)
    setEditContent(setting.content)
  }

  const handleSave = async () => {
    if (!selectedSetting) return

    setSaving(true)
    try {
      const response = await fetch(`/api/v1/settings/settings/${selectedSetting}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editContent }),
      })

      if (response.ok) {
        alert('Prompt saved successfully!')
        if (selectedTemplate) {
          loadSettings(selectedTemplate)
        }
      } else {
        alert('Failed to save prompt')
      }
    } catch (error) {
      alert('Error saving prompt: ' + error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="loading-screen">Loading prompts...</div>
  }

  const currentTemplate = templates.find(t => t.id === selectedTemplate)
  const currentSetting = settings.find(s => s.id === selectedSetting)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Prompt Settings</h1>
          <p className="page-description">
            Customize the AI agents that power WebMagic. Changes take effect immediately.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Agent Selection Sidebar */}
        <div className="lg:col-span-1 space-y-3">
          {templates.map((template) => {
            const Icon = AGENT_ICONS[template.agent_name] || Wrench
            return (
              <Card
                key={template.id}
                className={`cursor-pointer transition-all ${
                  selectedTemplate === template.id
                    ? 'ring-2 ring-primary'
                    : 'hover:bg-surface-hover'
                }`}
                onClick={() => setSelectedTemplate(template.id)}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-6 h-6 text-primary" />
                  <div>
                    <div className="font-semibold capitalize">
                      {template.agent_name.replace('_', ' ')}
                    </div>
                    <div className="text-sm text-secondary">
                      {template.sections_count} sections
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Sections List */}
        <div className="lg:col-span-3">
          {currentTemplate && (
            <Card>
              <div className="card-header">
                <h2 className="card-title capitalize">
                  {currentTemplate.agent_name.replace('_', ' ')} Prompts
                </h2>
                <div className="text-secondary">{currentTemplate.description}</div>
              </div>

              <div className="space-y-3">
                {settings.map((setting) => (
                  <div
                    key={setting.id}
                    className={`border border-border rounded-lg overflow-hidden transition-all ${
                      selectedSetting === setting.id ? 'ring-2 ring-primary' : ''
                    }`}
                  >
                    <div
                      className="p-4 cursor-pointer hover:bg-surface-hover"
                      onClick={() => handleSettingClick(setting)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{setting.section_name}</h3>
                          {setting.description && (
                            <p className="text-sm text-secondary mt-1">
                              {setting.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="badge badge-info">v{setting.version}</span>
                          <span className="text-secondary">
                            {selectedSetting === setting.id ? '▼' : '▶'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {selectedSetting === setting.id && (
                      <div className="p-4 bg-surface border-t border-border">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          rows={12}
                          className="input font-mono text-sm"
                          placeholder="Enter prompt content..."
                        />
                        <div className="flex justify-end gap-2 mt-3">
                          <button
                            onClick={() => setSelectedSetting(null)}
                            className="btn btn-secondary"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSave}
                            disabled={saving}
                            className="btn btn-primary"
                          >
                            {saving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {settings.length === 0 && (
                  <div className="text-center py-8 text-secondary">
                    No prompt sections available for this agent.
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
