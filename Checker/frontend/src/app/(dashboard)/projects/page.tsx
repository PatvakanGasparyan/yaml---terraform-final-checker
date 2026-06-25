'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { FileCode, Shield, ArrowRight, Layers, GitBranch } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { PageHeader } from '@/components/layout/page-header';
import { api, type PaginatedHistory } from '@/lib/api';
import { TEMPLATES, STATUS_STYLES } from '@/lib/constants';
import { useTranslations } from '@/hooks/use-translations';
import { cn } from '@/lib/utils';

export default function ProjectsPage() {
  const { t } = useTranslations();

  const { data: history, isLoading } = useQuery<PaginatedHistory>({
    queryKey: ['validation-history'],
    queryFn: () => api.get('/validations/history?page_size=50'),
  });

  const yamlCount = history?.items.filter((i) => i.validation_type === 'yaml').length ?? 0;
  const tfCount = history?.items.filter((i) => i.validation_type === 'terraform').length ?? 0;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader title={t('projects.title')} description={t('projects.subtitle')}>
          <Link href="/validations">
            <Button className="gap-2">
              {t('projects.newScan')} <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </PageHeader>

        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: Layers, label: t('projects.totalScans'), value: history?.total ?? 0, color: 'text-primary' },
            { icon: FileCode, label: t('projects.yamlScans'), value: yamlCount, color: 'text-cyan-500' },
            { icon: GitBranch, label: t('projects.tfScans'), value: tfCount, color: 'text-blue-500' },
          ].map((stat) => (
            <Card key={stat.label} className="glass-card stat-glow">
              <CardContent className="flex items-center gap-4 p-6">
                <div className={`rounded-xl bg-muted/50 p-3 ${stat.color}`}>
                  <stat.icon className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle>{t('projects.quickStart')}</CardTitle>
            <CardDescription>{t('projects.quickStartDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            {TEMPLATES.map((tpl) => (
              <Link key={tpl.id} href="/validations">
                <div className="group rounded-xl border p-4 transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md">
                  <FileCode className="mb-2 h-8 w-8 text-primary transition-transform group-hover:scale-110" />
                  <p className="font-medium">{tpl.label}</p>
                  <p className="text-xs text-muted-foreground">{tpl.path}</p>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              {t('projects.recentScans')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : (history?.items.length ?? 0) === 0 ? (
              <div className="py-12 text-center">
                <p className="mb-4 text-muted-foreground">{t('projects.noScans')}</p>
                <Link href="/validations">
                  <Button>{t('projects.startFirst')}</Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y rounded-lg border">
                {history!.items.map((item) => (
                  <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 p-4 hover:bg-muted/20">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">{item.validation_type}</Badge>
                        <Badge className={cn('capitalize', STATUS_STYLES[item.status])}>{item.status}</Badge>
                        {item.security_findings_count > 0 && (
                          <Badge variant="warning">{item.security_findings_count} security</Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{item.summary}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
