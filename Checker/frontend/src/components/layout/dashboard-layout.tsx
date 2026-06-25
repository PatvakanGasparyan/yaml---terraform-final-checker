'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  LayoutDashboard,
  FileCheck,
  FolderKanban,
  Settings,
  Moon,
  Sun,
  Menu,
  X,
  Globe,
  FileCode2,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/store/auth';
import { useTranslations } from '@/hooks/use-translations';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/dashboard', labelKey: 'common.dashboard', icon: LayoutDashboard },
  { href: '/validations', labelKey: 'common.validations', icon: FileCheck },
  { href: '/yaml-editor', labelKey: 'common.yamlEditor', icon: FileCode2 },
  { href: '/projects', labelKey: 'common.projects', icon: FolderKanban },
  { href: '/settings', labelKey: 'common.settings', icon: Settings },
];

const languages = [
  { code: 'en', label: 'English' },
  { code: 'ru', label: 'Русский' },
  { code: 'hy', label: 'Հայերեն' },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { t } = useTranslations();

  return (
    <nav className="flex flex-1 flex-col gap-1 p-4">
      {navItems.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link key={item.href} href={item.href} onClick={onNavigate}>
            <motion.div
              whileHover={{ x: 4 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive ? 'nav-link-active' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {t(item.labelKey)}
            </motion.div>
          </Link>
        );
      })}
    </nav>
  );
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useTheme();
  const { language, setLanguage } = useAppStore();
  const { t } = useTranslations();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border/60 bg-card/50 backdrop-blur-md md:flex">
        <Link href="/validations" className="flex items-center gap-2 border-b border-border/60 p-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Shield className="h-5 w-5 text-primary" />
          </div>
          <div>
            <span className="block text-sm font-bold leading-tight">YTV Platform</span>
            <span className="text-xs text-muted-foreground">Validator</span>
          </div>
        </Link>
        <NavLinks />
        <div className="mt-auto border-t border-border/60 p-4 text-xs text-muted-foreground">
          {t('common.appName')}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border/60 bg-background/80 px-4 py-3 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <Link href="/validations" className="flex items-center gap-2 md:hidden">
              <Shield className="h-5 w-5 text-primary" />
              <span className="font-semibold">YTV</span>
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border border-border/60 bg-muted/50 px-2 py-1">
              <Globe className="h-3.5 w-3.5 text-muted-foreground" />
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="bg-transparent text-sm outline-none"
                aria-label="Language"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label="Toggle theme"
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            </Button>
          </div>
        </header>

        {/* Mobile drawer */}
        <AnimatePresence>
          {mobileOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 bg-black/50 md:hidden"
                onClick={() => setMobileOpen(false)}
              />
              <motion.aside
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-card shadow-xl md:hidden"
              >
                <div className="flex items-center justify-between border-b p-4">
                  <span className="font-bold">{t('common.appName')}</span>
                  <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} aria-label="Close menu">
                    <X className="h-5 w-5" />
                  </Button>
                </div>
                <NavLinks onNavigate={() => setMobileOpen(false)} />
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        <main className="flex-1 overflow-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
