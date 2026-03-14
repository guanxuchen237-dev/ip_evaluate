/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module '@/api/mock_simulation' {
  export const mockReaderProfiles: any[]
  export const mockGraphDataMap: Record<string | number, any>
  export const mockBooks: any[]
}
