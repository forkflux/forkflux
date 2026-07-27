/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for the ForkFlux API (required when FE_USE_MOCKS is not "true"). */
  readonly FE_API_BASE_URL?: string;
  /** When "true", use the in-memory mock data source instead of the live API. */
  readonly FE_USE_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
