'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileCheck, LayoutDashboard, Moon, Shield, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/validate', label: 'Validate', icon: FileCheck },
  { href: '/validations', label: 'History', icon: FileCheck },
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/90 backdrop-blur-md">
        <div className="container mx-auto flex h-14 items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Shield className="h-4 w-4 text-primary" />
            </div>
            <span className="text-sm font-semibold tracking-tight sm:text-base">
              YAML & Terraform Validator
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href}>
                <span
                  className={cn(
                    'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    pathname === item.href || pathname.startsWith(`${item.href}/`)
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  {item.label}
                </span>
              </Link>
            ))}
            <Link href="/docs" className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground">
              API Docs
            </Link>
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/validate" className="md:hidden">
              <Button size="sm">Validate</Button>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label="Toggle theme"
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 dark:rotate-0 dark:scale-100" />
            </Button>
          </div>
        </div>
      </header>
      <main className="container mx-auto flex-1 px-4 py-8 sm:px-6 sm:py-10">{children}</main>
      <footer className="border-t border-border/60 py-6 text-center text-xs text-muted-foreground">
        YAML & Terraform AI Validator · Enterprise IaC validation platform
      </footer>
    </div>
  );
}
