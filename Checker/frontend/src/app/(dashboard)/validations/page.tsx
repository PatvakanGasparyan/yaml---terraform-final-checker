'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { History } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { PageHeader } from '@/components/layout/page-header';
import { ValidatorWorkspace } from '@/components/validation/validator-workspace';
import { api, type PaginatedHistory } from '@/lib/api';
import { STATUS_STYLES } from '@/lib/constants';
import { useTranslations } from '@/hooks/use-translations';
import { cn } from '@/lib/utils';

export default function ValidationsPage() {
  const { t } = useTranslations();
  const queryClient = useQueryClient();

  const { data: history, isLoading: historyLoading, isError: historyError, refetch: refetchHistory } =
    useQuery<PaginatedHistory>({
      queryKey: ['validation-history'],
      queryFn: () => api.get('/validations/history?page_size=10'),
      retry: 2,
    });

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader title={t('validation.title')} description={t('validation.subtitle')} />

        <ValidatorWorkspace
          onValidated={() => {
            queryClient.invalidateQueries({ queryKey: ['validation-history'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }}
        />

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <History className="h-5 w-5" />
              {t('validation.history')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {historyError ? (
              <div className="py-6 text-center">
                <p className="mb-3 text-sm text-muted-foreground">{t('dashboard.errorTitle')}</p>
                <Button variant="outline" size="sm" onClick={() => refetchHistory()}>
                  {t('common.retry')}
                </Button>
              </div>
            ) : historyLoading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : (history?.items.length ?? 0) === 0 ? (
              <p className="py-6 text-center text-muted-foreground">{t('validation.noHistory')}</p>
            ) : (
              <div className="divide-y rounded-lg border">
                {history!.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-2 p-4 transition-colors hover:bg-muted/30"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{item.validation_type}</Badge>
                        <Badge className={cn('capitalize', STATUS_STYLES[item.status])}>{item.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {item.summary || `${item.error_count} errors, ${item.warning_count} warnings`}
                      </p>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      {new Date(item.created_at).toLocaleString()}
                      {item.duration_ms != null && <div>{item.duration_ms}ms</div>}
                    </div>
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
