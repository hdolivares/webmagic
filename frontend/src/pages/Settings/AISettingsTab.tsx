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
  validation: {
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
  savedProvider?: string;
  savedModel?: string;
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
  savedProvider,
  savedModel,
  providers,
  onProviderChange,
  onModelChange,
  providerKeyName,
  modelKeyName,
}) => {
  const providerData = providers[currentProvider];
  const hasChanges = savedProvider !== currentProvider || savedModel !== currentModel;

  return (
    <div className="model-selector">
      <div className="model-selector__header">
        <h3 className="model-selector__label">{label}</h3>
        <p className="model-selector__description">{description}</p>
      </div>

      {/* Current Configuration Display */}
      {savedProvider && savedModel && (
        <div className="model-selector__current">
          <div className="model-selector__current-label">Current Configuration:</div>
          <div className="model-selector__current-values">
            <span className="model-selector__current-badge">
              {providers[savedProvider]?.name || savedProvider}
            </span>
            <span className="model-selector__current-separator">•</span>
            <span className="model-selector__current-model">{savedModel}</span>
          </div>
        </div>
      )}

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
    </div>
  );
};

// Main Component
export const AISettingsTab: React.FC = () => {
  const queryClient = useQueryClient();
  
  // State for form values
  const [llmProvider, setLlmProvider] = useState<string>('');
  const [llmModel, setLlmModel] = useState<string>('');
  const [validationProvider, setValidationProvider] = useState<string>('');
  const [validationModel, setValidationModel] = useState<string>('');
  const [imageProvider, setImageProvider] = useState<string>('');
  const [imageModel, setImageModel] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch current AI configuration
  const { data: aiConfig, isLoading: configLoading } = useQuery<AIConfig>({
    queryKey: ['aiConfig'],
    queryFn: () => api.getAIConfig(),
  });

  // Fetch available providers
  const { data: providers, isLoading: providersLoading } = useQuery<ProvidersData>({
    queryKey: ['aiProviders'],
    queryFn: () => api.getAIProviders(),
  });

  // Initialize form state when data loads
  useEffect(() => {
    if (aiConfig) {
      setLlmProvider(aiConfig.llm.provider);
      setLlmModel(aiConfig.llm.model);
      // Handle validation config (fallback to llm if not present)
      setValidationProvider(aiConfig.validation?.provider || aiConfig.llm.provider);
      setValidationModel(aiConfig.validation?.model || 'claude-3-haiku-20240307');
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
      validationProvider !== (aiConfig.validation?.provider || aiConfig.llm.provider) ||
      validationModel !== (aiConfig.validation?.model || 'claude-3-haiku-20240307') ||
      imageProvider !== aiConfig.image.provider ||
      imageModel !== aiConfig.image.model;
    
    setHasChanges(changed);
  }, [llmProvider, llmModel, validationProvider, validationModel, imageProvider, imageModel, aiConfig]);

  // Mutation to update settings
  const updateSettingMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      return api.updateSystemSetting(key, value);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aiConfig'] });
    },
  });

  // Save all changes
  const handleSave = async () => {
    try {
      // Update all 6 settings
      await Promise.all([
        updateSettingMutation.mutateAsync({ key: 'llm_provider', value: llmProvider }),
        updateSettingMutation.mutateAsync({ key: 'llm_model', value: llmModel }),
        updateSettingMutation.mutateAsync({ key: 'validation_provider', value: validationProvider }),
        updateSettingMutation.mutateAsync({ key: 'validation_model', value: validationModel }),
        updateSettingMutation.mutateAsync({ key: 'image_provider', value: imageProvider }),
        updateSettingMutation.mutateAsync({ key: 'image_model', value: imageModel }),
      ]);

      setHasChanges(false);
      
      // Show success message
      alert('AI settings updated successfully! Changes will take effect immediately.');
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
      setValidationProvider(aiConfig.validation?.provider || aiConfig.llm.provider);
      setValidationModel(aiConfig.validation?.model || 'claude-3-haiku-20240307');
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
          Configure which AI models to use for website validation, generation, and image creation.
          Changes take effect immediately.
        </p>
      </div>

      {/* Validation Model Configuration */}
      <Card>
        <ModelSelector
          label="✅ Website Validation Model"
          description="Used for fast, cost-effective website validation (verifying URLs, checking content)"
          currentProvider={validationProvider}
          currentModel={validationModel}
          savedProvider={aiConfig.validation?.provider || aiConfig.llm.provider}
          savedModel={aiConfig.validation?.model || 'claude-3-haiku-20240307'}
          providers={providers.llm}
          onProviderChange={(provider) => {
            setValidationProvider(provider);
            // Auto-select first model of new provider
            const firstModel = providers.llm[provider]?.models[0]?.id;
            if (firstModel) setValidationModel(firstModel);
          }}
          onModelChange={setValidationModel}
          providerKeyName="validation_provider"
          modelKeyName="validation_model"
        />
      </Card>

      {/* Generation Model Configuration */}
      <Card>
        <ModelSelector
          label="🧠 Website Generation Model"
          description="Used for AI website generation: Analyst, Concept, Art Director, and Architect agents"
          currentProvider={llmProvider}
          currentModel={llmModel}
          savedProvider={aiConfig.llm.provider}
          savedModel={aiConfig.llm.model}
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
          savedProvider={aiConfig.image.provider}
          savedModel={aiConfig.image.model}
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
            <li><strong>Validation Model:</strong> Use faster, cheaper models (e.g., Claude 3 Haiku) for website validation tasks</li>
            <li><strong>Generation Model:</strong> Use more capable models (e.g., Claude Sonnet 4) for high-quality website generation</li>
            <li>Different models have different costs and capabilities</li>
            <li>Recommended models are marked for best results</li>
            <li>Make sure you have valid API keys configured in environment variables</li>
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
    </div>
  );
};
