'use client';

import { useTheme } from 'next-themes';
import { useQuery } from '@tanstack/react-query';
import { Globe, Sun, Moon, Monitor, Palette, Languages, Sparkles, Bot } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { PageHeader } from '@/components/layout/page-header';
import { useAppStore } from '@/store/auth';
import { useTranslations } from '@/hooks/use-translations';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SystemConfig {
  ai: {
    provider: string;
    model: string;
    configured: boolean;
    temperature: number;
    max_tokens: number;
    custom_prompt: boolean;
  };
}

const themes = [
  { id: 'light', icon: Sun, labelKey: 'settings.themeLight' },
  { id: 'dark', icon: Moon, labelKey: 'settings.themeDark' },
  { id: 'system', icon: Monitor, labelKey: 'settings.themeSystem' },
] as const;

const languages = [
  { code: 'en', label: 'English', flag: '🇺🇸' },
  { code: 'ru', label: 'Русский', flag: '🇷🇺' },
  { code: 'hy', label: 'Հայերեն', flag: '🇦🇲' },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { language, setLanguage } = useAppStore();
  const { t } = useTranslations();

  const { data: systemConfig } = useQuery<SystemConfig>({
    queryKey: ['system-config'],
    queryFn: () => api.get('/system/config'),
  });

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader title={t('settings.title')} description={t('settings.subtitle')} />

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              {t('settings.appearance')}
            </CardTitle>
            <CardDescription>{t('settings.appearanceDesc')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {themes.map((th) => (
                <button
                  key={th.id}
                  type="button"
                  onClick={() => setTheme(th.id)}
                  className={cn(
                    'flex flex-col items-center gap-2 rounded-xl border p-4 transition-all hover:border-primary/50',
                    theme === th.id && 'border-primary bg-primary/5 shadow-md shadow-primary/10'
                  )}
                >
                  <th.icon className="h-6 w-6" />
                  <span className="text-sm font-medium">{t(th.labelKey)}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Languages className="h-5 w-5" />
              {t('settings.language')}
            </CardTitle>
            <CardDescription>{t('settings.languageDesc')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setLanguage(lang.code)}
                  className={cn(
                    'flex items-center gap-3 rounded-lg border p-3 text-left transition-all hover:border-primary/50',
                    language === lang.code && 'border-primary bg-primary/5'
                  )}
                >
                  <span className="text-xl">{lang.flag}</span>
                  <span className="font-medium">{lang.label}</span>
                  {language === lang.code && (
                    <span className="ml-auto text-xs text-primary">{t('settings.active')}</span>
                  )}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              {t('settings.ai')}
            </CardTitle>
            <CardDescription>{t('settings.aiDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <Bot className="h-3.5 w-3.5" />
                  {t('settings.aiProvider')}
                </div>
                <p className="font-semibold capitalize">{systemConfig?.ai.provider ?? '—'}</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {t('settings.aiModel')}
                </div>
                <p className="font-semibold">{systemConfig?.ai.model ?? '—'}</p>
              </div>
            </div>
            <div
              className={cn(
                'flex items-center gap-3 rounded-lg border p-4',
                systemConfig?.ai.configured
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : 'border-amber-500/30 bg-amber-500/5'
              )}
            >
              <Sparkles
                className={cn('h-5 w-5', systemConfig?.ai.configured ? 'text-emerald-500' : 'text-amber-500')}
              />
              <div>
                <p className="text-sm font-medium">{t('settings.aiStatus')}</p>
                <p className="text-sm text-muted-foreground">
                  {systemConfig?.ai.configured ? t('settings.aiReady') : t('settings.aiFallback')}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">{t('settings.aiPrompt')}</p>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              {t('settings.about')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>{t('settings.aboutDesc')}</p>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" asChild>
                <a href="/docs" target="_blank" rel="noopener noreferrer">
                  API Docs
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
