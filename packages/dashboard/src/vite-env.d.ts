/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for the ForkFlux API (non-dev environments). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
