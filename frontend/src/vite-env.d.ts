/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_SERVER_IP?: string
  readonly VITE_SMS_SENDER_NUMBER?: string
  readonly VITE_SITES_BASE_URL?: string
  readonly VITE_PORTAL_URL?: string
  readonly VITE_CONTACT_EMAIL?: string
  // add more env variables as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
