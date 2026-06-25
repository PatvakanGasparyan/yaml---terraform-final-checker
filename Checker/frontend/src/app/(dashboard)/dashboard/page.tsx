'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart,
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Shield,
  FileCode,
  Brain,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { PageHeader } from '@/components/layout/page-header';
import { api, type DashboardData } from '@/lib/api';
import { useTranslations } from '@/hooks/use-translations';

const statConfig = [
  { key: 'total_scans', labelKey: 'dashboard.totalScans', icon: Activity, color: 'text-primary' },
  { key: 'successful_validations', labelKey: 'dashboard.successfulValidations', icon: CheckCircle, color: 'text-emerald-500' },
  { key: 'failed_validations', labelKey: 'dashboard.failedValidations', icon: AlertTriangle, color: 'text-red-500' },
  { key: 'security_findings', labelKey: 'dashboard.securityFindings', icon: Shield, color: 'text-orange-500' },
  { key: 'terraform_projects', labelKey: 'dashboard.terraformProjects', icon: FileCode, color: 'text-blue-500' },
  { key: 'yaml_projects', labelKey: 'dashboard.yamlProjects', icon: FileCode, color: 'text-cyan-500' },
  { key: 'ai_recommendations', labelKey: 'dashboard.aiRecommendations', icon: Brain, color: 'text-violet-500' },
] as const;

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  delay,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  color: string;
  delay: number;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }} className="stat-glow">
      <Card className="glass-card overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
          <div className={`rounded-lg bg-muted/50 p-2 ${color}`}>
            <Icon className="h-4 w-4" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight">{value.toLocaleString()}</div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function DashboardPage() {
  const { t } = useTranslations();
  const { data, isLoading, isError, error, refetch } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard'),
    refetchInterval: 30000,
  });

  const stats = data?.stats;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader title={t('dashboard.title')} description={t('dashboard.subtitle')}>
          <Link href="/validations">
            <Button className="gap-2">
              {t('dashboard.newValidation')} <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </PageHeader>

        {isError && (
          <Alert variant="destructive">
            <AlertTitle>{t('dashboard.errorTitle')}</AlertTitle>
            <AlertDescription className="flex items-center justify-between gap-4">
              <span>{error.message}</span>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                {t('common.retry')}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[...Array(7)].map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {statConfig.map((cfg, i) => (
              <StatCard
                key={cfg.key}
                title={t(cfg.labelKey)}
                value={stats?.[cfg.key] ?? 0}
                icon={cfg.icon}
                color={cfg.color}
                delay={i * 0.05}
              />
            ))}
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>{t('dashboard.validationTrends')}</CardTitle>
              <CardDescription>{t('dashboard.last30Days')}</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-[260px] w-full" />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={data?.charts.validation_trends ?? []}>
                    <defs>
                      <linearGradient id="valGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="hsl(var(--primary))" fill="url(#valGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle>{t('dashboard.securityTrends')}</CardTitle>
              <CardDescription>{t('dashboard.last30Days')}</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-[260px] w-full" />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={data?.charts.security_trends ?? []}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {data?.ai_recommendations && data.ai_recommendations.length > 0 && (
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-violet-500" />
                  {t('dashboard.aiRecommendations')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {data.ai_recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-3 rounded-lg border bg-muted/20 p-3 text-sm">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                {t('dashboard.recentActivity')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : (data?.recent_activity.length ?? 0) === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">{t('dashboard.noActivity')}</p>
              ) : (
                <div className="space-y-2">
                  {data!.recent_activity.map((item) => (
                    <div key={item.id} className="flex items-start justify-between gap-2 rounded-lg border p-3 text-sm">
                      <div>
                        <p className="font-medium">{item.title}</p>
                        <p className="text-xs text-muted-foreground">{item.user_name}</p>
                      </div>
                      <Badge variant="outline" className="shrink-0 text-xs">
                        {new Date(item.created_at).toLocaleDateString()}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
