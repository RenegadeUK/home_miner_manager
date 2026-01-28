# React Migration Notes — AI Settings

## Legacy Template Overview
- Template: `app/ui/templates/settings/openai.html` rendered via `/settings/openai` route.
- Page contains two independent cards/forms: **OpenAI (cloud)** and **Ollama (local)**.
- Each form owns its own enable toggle, fields, and submission button. Only one provider is persisted at a time via `provider` value in the POST payload.

## OpenAI Form Behaviors
- Fields: enable toggle, API key (`sk-…`), model select (`gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`), max tokens (100–4000, step 100).
- API key input is masked; if a key already exists, the template inserts the `●●●●●●●●●●●●●●●●` placeholder instead of the actual secret.
- Buttons next to the key input:
  - "Eye" toggle switches between password/text visibility (per-provider icon IDs).
  - "Test" button triggers `testOpenAIConnection()` which POSTs to `/api/ai/test` with `{ provider: 'openai', api_key, model, base_url: 'https://api.openai.com/v1' }`.
- Save submits the form to `/api/ai/config` (JSON). API key is only included if the user provided a non-placeholder value, mirroring the backend logic that keeps the stored key intact when omitted.
- Help text links to OpenAI dashboard and clarifies storage expectations.

## Ollama Form Behaviors
- Fields: enable toggle, base URL (default `http://localhost:11434/v1`), model select (predefined list + "Custom" option), custom model text box (hidden until "Custom" selected), max tokens, helper alert block.
- Buttons: "Test" sends `{ provider: 'ollama', base_url, model }` to `/api/ai/test`. On success the backend verifies connectivity and whether the model is available.
- Save posts to `/api/ai/config` with `provider: 'ollama'`, includes `base_url`, `model`, `max_tokens`, and sets `api_key: 'ollama'` as placeholder since secrets are not required.

## Shared Logic
- `loadConfig()` fetches `/api/ai/config` on page load, then:
  - Populates OpenAI controls if `provider` is `openai` (including placeholder key when `api_key` is present).
  - Otherwise fills Ollama fields (base URL, model, toggles). If stored model doesn’t match predefined options, the script selects "Custom" and shows the extra input.
- Helper DOM utilities: `toggleApiKeyVisibility()`, `showKeyStatus()`, and two async test functions that write status text (success/error/info) into provider-specific divs for 5 seconds.
- Both forms present blocking `alert()` success/error dialogs after save attempts; there is no toast system.

## API Surface Used
- `GET /api/ai/config`: returns `{ enabled, provider, model, max_tokens, base_url?, api_key? }` (masked string when stored).
- `POST /api/ai/config`: accepts `enabled`, `provider`, `model`, `max_tokens`, `base_url?`, `api_key?`. Backend keeps the prior API key when the placeholder string is omitted.
- `POST /api/ai/test`: accepts `{ provider: 'openai' | 'ollama', model, api_key?, base_url? }` and returns `{ success, message?, error?, model? }`.

## Migration Considerations
- React form should keep **separate state** for OpenAI + Ollama while reflecting whichever provider is currently stored.
- Preserve masked API key semantics: display "Stored securely" when backend signals a value but do not set the input to the placeholder string.
- Form validation requirements:
  - OpenAI: API key required when enabling without a stored secret; max tokens clamped between 100–4000.
  - Ollama: Base URL required; custom model required when "Custom" selected.
- Provide inline success/error messaging instead of `alert()` dialogs, and expose test results in-context (per provider) like the legacy `showKeyStatus()` function.
- Remember backend expects Ollama saves to include an `api_key` value (legacy sends `'ollama'`), even though it is unused.
