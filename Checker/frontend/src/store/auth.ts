import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  language: string;
  setLanguage: (lang: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: 'en',
      setLanguage: (lang) => set({ language: lang }),
    }),
    { name: 'app-storage' }
  )
);

/** @deprecated Use useAppStore */
export const useAuthStore = useAppStore;
