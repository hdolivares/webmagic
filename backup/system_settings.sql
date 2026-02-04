-- Dump of system_settings table
-- Generated: 2026-02-04
-- Rows: 4

INSERT INTO system_settings (id, key, value, value_type, category, label, description, options, is_secret, is_required, default_value, created_at, updated_at) VALUES
('ae6b69a9-a43f-4db6-a886-cfd54f910ef2', 'llm_provider', 'anthropic', 'string', 'ai', 'LLM Provider', 'Primary AI provider for text generation (agents)', '[{"label": "Anthropic (Claude)", "value": "anthropic"}, {"label": "Google (Gemini)", "value": "google"}, {"label": "OpenAI (GPT)", "value": "openai"}]', false, false, NULL, '2026-01-21T04:10:55.480Z', '2026-01-21T04:10:55.480Z'),
('f7e194eb-f851-453d-843b-ef107711bcf8', 'image_provider', 'google', 'string', 'ai', 'Image Generation Provider', 'Provider for AI image generation', '[{"label": "Google (Imagen)", "value": "google"}, {"label": "OpenAI (DALL-E)", "value": "openai"}]', false, false, NULL, '2026-01-21T04:10:55.708Z', '2026-01-21T04:10:55.708Z'),
('38a25f86-65c2-498f-bc63-427bb33188b3', 'image_model', 'imagen-3.0-generate-001', 'string', 'ai', 'Image Generation Model', 'Specific image generation model', NULL, false, false, NULL, '2026-01-21T04:10:55.799Z', '2026-01-21T04:10:55.799Z'),
('e2acdd55-c1ed-44f3-9cdb-c23bf3f22a3e', 'llm_model', 'claude-sonnet-4-5', 'string', 'ai', 'LLM Model', 'Specific model to use for agents (Analyst, Concept, Art Director, Architect)', NULL, false, false, NULL, '2026-01-21T04:10:55.618Z', '2026-01-21T04:10:55.618Z');

