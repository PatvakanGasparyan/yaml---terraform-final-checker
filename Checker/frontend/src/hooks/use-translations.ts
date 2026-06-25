'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAppStore } from '@/store/auth';
import enMessages from '@/i18n/messages/en.json';

type Messages = Record<string, unknown>;

const bundled: Record<string, Messages> = {
  en: enMessages as Messages,
};

const cache: Partial<Record<string, Messages>> = { en: enMessages as Messages };

async function loadLocale(lang: string): Promise<Messages> {
  if (cache[lang]) return cache[lang]!;
  if (bundled[lang]) {
    cache[lang] = bundled[lang];
    return bundled[lang];
  }
  try {
    const res = await fetch(`/locales/${lang}/common.json`);
    if (res.ok) {
      const data = await res.json();
      cache[lang] = data;
      return data;
    }
  } catch {
    /* use fallback */
  }
  return enMessages as Messages;
}

function getNested(obj: Messages, path: string): string {
  const keys = path.split('.');
  let current: unknown = obj;
  for (const key of keys) {
    if (current && typeof current === 'object' && key in (current as object)) {
      current = (current as Record<string, unknown>)[key];
    } else {
      return path;
    }
  }
  return typeof current === 'string' ? current : path;
}

export function useTranslations() {
  const language = useAppStore((s) => s.language);
  const [messages, setMessages] = useState<Messages>(enMessages as Messages);

  useEffect(() => {
    loadLocale(language).then(setMessages);
  }, [language]);

  const t = useCallback(
    (key: string, fallback?: string) => {
      const value = getNested(messages, key);
      if (value !== key) return value;
      const enValue = getNested(enMessages as Messages, key);
      if (enValue !== key) return enValue;
      return fallback ?? key;
    },
    [messages]
  );

  return { t, language };
}
