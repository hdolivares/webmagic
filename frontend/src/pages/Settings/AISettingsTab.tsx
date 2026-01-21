import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../services/api';
import { Card } from '../../components/ui';
import './AISettingsTab.css';

// Types
interface AIProvider {
  name: string;
  models: Array<{
    id: string;
    name: string;
    recommended?: boolean;
  }>;
  requires_key: string;
}

interface AIConfig {
  llm: {
    provider: string;
    model: string;
    provider_info: AIProvider;
  };
  image: {
    provider: string;
    model: string;
    provider_info: AIProvider;
  };
}

interface ProvidersData {
  llm: Record<string, AIProvider>;
  image: Record<string, AIProvider>;
}

// Reusable ModelSelector Component
const ModelSelector: React.FC<{
  label: string;
  description: string;
  currentProvider: string;
  currentModel: string;
  providers: Record<string, AIProvider>;
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string) => void;
  providerKeyName: string;
  modelKeyName: string;
}> = ({
  label,
  description,
  currentProvider,
  currentModel,
  providers,
  onProviderChange,
  onModelChange,
  providerKeyName,
  modelKeyName,
}) => {
  const providerData = providers[currentProvider];

  return (
    <div className="model-selector">
      <div className="model-selector__header">
        <h3 className="model-selector__label">{label}</h3>
        <p className="model-selector__description">{description}</p>
      </div>

      {/* Provider Selection */}
      <div className="model-selector__field">
        <label htmlFor={providerKeyName} className="model-selector__field-label">
          Provider
        </label>
        <select
          id={providerKeyName}
          className="model-selector__select"
          value={currentProvider}
          onChange={(e) => onProviderChange(e.target.value)}
        >
          {Object.entries(providers).map(([key, provider]) => (
            <option key={key} value={key}>
              {provider.name}
            </option>
          ))}
        </select>
      </div>

      {/* Model Selection */}
      <div className="model-selector__field">
        <label htmlFor={modelKeyName} className="model-selector__field-label">
          Model
        </label>
        <select
          id={modelKeyName}
          className="model-selector__select"
          value={currentModel}
          onChange={(e) => onModelChange(e.target.value)}
        >
          {providerData?.models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name}
              {model.recommended ? ' (Recommended)' : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Info Message */}
      {providerData && (
        <div className="model-selector__info">
          <span className="model-selector__info-icon">ℹ️</span>
          <span className="model-selector__info-text">
            Requires API key: <code>{providerData.requires_key}</code>
          </span>
        </div>
      )}
    </div>
  );
};

// Main Component
export const AISettingsTab: React.FC = () => {
  const queryClient = useQueryClient();
  
  // State for form values
  const [llmProvider, setLlmProvider] = useState<string>('');
  const [llmModel, setLlmModel] = useState<string>('');
  const [imageProvider, setImageProvider] = useState<string>('');
  const [imageModel, setImageModel] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch current AI configuration
  const { data: aiConfig, isLoading: configLoading } = useQuery<AIConfig>({
    queryKey: ['aiConfig'],
    queryFn: () => api.get('/system/ai-config').then((res) => res.data),
  });

  // Fetch available providers
  const { data: providers, isLoading: providersLoading } = useQuery<ProvidersData>({
    queryKey: ['aiProviders'],
    queryFn: () => api.get('/system/ai-providers').then((res) => res.data),
  });

  // Initialize form state when data loads
  useEffect(() => {
    if (aiConfig) {
      setLlmProvider(aiConfig.llm.provider);
      setLlmModel(aiConfig.llm.model);
      setImageProvider(aiConfig.image.provider);
      setImageModel(aiConfig.image.model);
    }
  }, [aiConfig]);

  // Check for changes
  useEffect(() => {
    if (!aiConfig) return;
    
    const changed =
      llmProvider !== aiConfig.llm.provider ||
      llmModel !== aiConfig.llm.model ||
      imageProvider !== aiConfig.image.provider ||
      imageModel !== aiConfig.image.model;
    
    setHasChanges(changed);
  }, [llmProvider, llmModel, imageProvider, imageModel, aiConfig]);

  // Mutation to update settings
  const updateSettingMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      return api.post('/system/settings', { key, value });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aiConfig'] });
    },
  });

  // Save all changes
  const handleSave = async () => {
    try {
      // Update all 4 settings
      await Promise.all([
        updateSettingMutation.mutateAsync({ key: 'llm_provider', value: llmProvider }),
        updateSettingMutation.mutateAsync({ key: 'llm_model', value: llmModel }),
        updateSettingMutation.mutateAsync({ key: 'image_provider', value: imageProvider }),
        updateSettingMutation.mutateAsync({ key: 'image_model', value: imageModel }),
      ]);

      setHasChanges(false);
      
      // Show success message
      alert('AI settings updated successfully! Changes will take effect on next generation.');
    } catch (error) {
      console.error('Failed to update settings:', error);
      alert('Failed to update settings. Please try again.');
    }
  };

  // Reset to current saved values
  const handleReset = () => {
    if (aiConfig) {
      setLlmProvider(aiConfig.llm.provider);
      setLlmModel(aiConfig.llm.model);
      setImageProvider(aiConfig.image.provider);
      setImageModel(aiConfig.image.model);
      setHasChanges(false);
    }
  };

  // Loading state
  if (configLoading || providersLoading) {
    return (
      <div className="ai-settings-tab">
        <Card>
          <div className="ai-settings-tab__loading">
            <div className="ai-settings-tab__spinner"></div>
            <p>Loading AI configuration...</p>
          </div>
        </Card>
      </div>
    );
  }

  // Error state
  if (!aiConfig || !providers) {
    return (
      <div className="ai-settings-tab">
        <Card>
          <div className="ai-settings-tab__error">
            <span className="ai-settings-tab__error-icon">⚠️</span>
            <p>Failed to load AI configuration</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="ai-settings-tab">
      {/* Header */}
      <div className="ai-settings-tab__header">
        <h2 className="ai-settings-tab__title">AI Model Configuration</h2>
        <p className="ai-settings-tab__subtitle">
          Configure which AI models to use for website generation and image creation.
          Changes take effect immediately on next generation.
        </p>
      </div>

      {/* LLM Configuration */}
      <Card>
        <ModelSelector
          label="🧠 Language Model (LLM)"
          description="Used for all AI agents: Analyst, Concept, Art Director, and Architect"
          currentProvider={llmProvider}
          currentModel={llmModel}
          providers={providers.llm}
          onProviderChange={(provider) => {
            setLlmProvider(provider);
            // Auto-select first model of new provider
            const firstModel = providers.llm[provider]?.models[0]?.id;
            if (firstModel) setLlmModel(firstModel);
          }}
          onModelChange={setLlmModel}
          providerKeyName="llm_provider"
          modelKeyName="llm_model"
        />
      </Card>

      {/* Image Configuration */}
      <Card>
        <ModelSelector
          label="🖼️ Image Generation Model"
          description="Used for generating hero images, backgrounds, and service images"
          currentProvider={imageProvider}
          currentModel={imageModel}
          providers={providers.image}
          onProviderChange={(provider) => {
            setImageProvider(provider);
            // Auto-select first model of new provider
            const firstModel = providers.image[provider]?.models[0]?.id;
            if (firstModel) setImageModel(firstModel);
          }}
          onModelChange={setImageModel}
          providerKeyName="image_provider"
          modelKeyName="image_model"
        />
      </Card>

      {/* Info Box */}
      <div className="ai-settings-tab__info-box">
        <div className="ai-settings-tab__info-box-icon">💡</div>
        <div className="ai-settings-tab__info-box-content">
          <h4 className="ai-settings-tab__info-box-title">About AI Models</h4>
          <ul className="ai-settings-tab__info-box-list">
            <li>Different models have different costs and capabilities</li>
            <li>Recommended models are marked for best results</li>
            <li>Make sure you have valid API keys configured in environment variables</li>
            <li>Model changes apply to all new website generations immediately</li>
          </ul>
        </div>
      </div>

      {/* Action Buttons */}
      {hasChanges && (
        <div className="ai-settings-tab__actions">
          <button
            className="ai-settings-tab__button ai-settings-tab__button--secondary"
            onClick={handleReset}
            disabled={updateSettingMutation.isPending}
          >
            Reset Changes
          </button>
          <button
            className="ai-settings-tab__button ai-settings-tab__button--primary"
            onClick={handleSave}
            disabled={updateSettingMutation.isPending}
          >
            {updateSettingMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      )}

      {/* Current Configuration Display */}
      <Card>
        <div className="ai-settings-tab__current-config">
          <h3 className="ai-settings-tab__current-config-title">Current Configuration</h3>
          <div className="ai-settings-tab__current-config-grid">
            <div className="ai-settings-tab__config-item">
              <span className="ai-settings-tab__config-label">LLM Provider:</span>
              <code className="ai-settings-tab__config-value">
                {aiConfig.llm.provider_info.name}
              </code>
            </div>
            <div className="ai-settings-tab__config-item">
              <span className="ai-settings-tab__config-label">LLM Model:</span>
              <code className="ai-settings-tab__config-value">{aiConfig.llm.model}</code>
            </div>
            <div className="ai-settings-tab__config-item">
              <span className="ai-settings-tab__config-label">Image Provider:</span>
              <code className="ai-settings-tab__config-value">
                {aiConfig.image.provider_info.name}
              </code>
            </div>
            <div className="ai-settings-tab__config-item">
              <span className="ai-settings-tab__config-label">Image Model:</span>
              <code className="ai-settings-tab__config-value">{aiConfig.image.model}</code>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
