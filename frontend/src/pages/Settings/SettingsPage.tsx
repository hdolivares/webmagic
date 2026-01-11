/**
 * Prompt settings editor page
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Button } from '@/components/ui'
import { Settings, Save, AlertCircle } from 'lucide-react'
import type { PromptTemplate, PromptSetting } from '@/types'

export const SettingsPage = () => {
  const queryClient = useQueryClient()
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [editedSettings, setEditedSettings] = useState<Record<string, string>>({})
  const [saveMessage, setSaveMessage] = useState<string>('')

  const { data: templates } = useQuery({
    queryKey: ['prompt-templates'],
    queryFn: () => api.getPromptTemplates(),
  })

  const { data: settings, isLoading } = useQuery({
    queryKey: ['prompt-settings', selectedTemplate],
    queryFn: () => api.getPromptSettings(selectedTemplate),
    enabled: !!selectedTemplate,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) =>
      api.updatePromptSetting(id, { setting_value: value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt-settings', selectedTemplate] })
      setSaveMessage('Settings saved successfully!')
      setTimeout(() => setSaveMessage(''), 3000)
    },
  })

  const handleSave = (settingId: string) => {
    const newValue = editedSettings[settingId]
    if (newValue !== undefined) {
      updateMutation.mutate({ id: settingId, value: newValue })
    }
  }

  const handleChange = (settingId: string, value: string) => {
    setEditedSettings((prev) => ({ ...prev, [settingId]: value }))
  }

  return (
    <div className="p-xl">
      <div className="mb-xl">
        <h1 className="text-4xl font-bold text-text-primary mb-2">Prompt Settings</h1>
        <p className="text-text-secondary">Configure LLM agent prompts and parameters</p>
      </div>

      {/* Template selector */}
      <Card className="mb-md">
        <CardHeader>
          <CardTitle>Select Agent</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            {templates?.map((template) => (
              <button
                key={template.id}
                onClick={() => setSelectedTemplate(template.id)}
                className={`p-md rounded-md border transition-all ${
                  selectedTemplate === template.id
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900'
                    : 'border-border hover:border-primary-400'
                }`}
              >
                <div className="flex items-center gap-md">
                  <Settings className="w-5 h-5" />
                  <div className="text-left">
                    <p className="font-medium">{template.name}</p>
                    <p className="text-xs text-text-secondary">{template.agent_type}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Settings editor */}
      {selectedTemplate && (
        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>Agent Settings</CardTitle>
            {saveMessage && (
              <div className="flex items-center gap-sm text-success text-sm">
                <AlertCircle className="w-4 h-4" />
                {saveMessage}
              </div>
            )}
          </CardHeader>
          <CardBody>
            {isLoading ? (
              <div className="flex items-center justify-center py-xl">
                <div className="spinner-lg" />
              </div>
            ) : (
              <div className="space-y-lg">
                {settings?.map((setting) => (
                  <div key={setting.id} className="space-y-sm">
                    <label className="label">
                      {setting.setting_key}
                      {setting.description && (
                        <span className="text-xs text-text-tertiary ml-sm">
                          ({setting.description})
                        </span>
                      )}
                    </label>
                    <textarea
                      value={editedSettings[setting.id] ?? setting.setting_value}
                      onChange={(e) => handleChange(setting.id, e.target.value)}
                      className="textarea"
                      rows={4}
                    />
                    <Button
                      size="sm"
                      onClick={() => handleSave(setting.id)}
                      disabled={editedSettings[setting.id] === undefined}
                      leftIcon={<Save className="w-4 h-4" />}
                    >
                      Save
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  )
}
