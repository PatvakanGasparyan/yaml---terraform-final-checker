'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Play,
  Upload,
  FileText,
  History,
  Loader2,
  Sparkles,
  FileCode2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { PageHeader } from '@/components/layout/page-header';
import { ValidationResults } from '@/components/validation/validation-results';
import { YamlCodeEditor } from '@/components/yaml/yaml-code-editor';
import { api, type PaginatedHistory, type ValidationResult } from '@/lib/api';
import { SAMPLE_YAML, TEMPLATES, STATUS_STYLES } from '@/lib/constants';
import { useTranslations } from '@/hooks/use-translations';
import { cn } from '@/lib/utils';

export default function ValidationsPage() {
  const { t } = useTranslations();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [content, setContent] = useState(SAMPLE_YAML);
  const [filePath, setFilePath] = useState('deployment.yaml');
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [includeAi, setIncludeAi] = useState(true);

  const { data: history, isLoading: historyLoading, isError: historyError, refetch: refetchHistory } = useQuery<PaginatedHistory>({
    queryKey: ['validation-history'],
    queryFn: () => api.get('/validations/history?page_size=10'),
    retry: 2,
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post<ValidationResult>('/validations/run', {
        content,
        file_path: filePath,
        validation_type: 'auto',
        include_ai_analysis: includeAi,
        include_security_scan: true,
      }),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ['validation-history'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const loadTemplate = (template: (typeof TEMPLATES)[number]) => {
    setFilePath(template.path);
    setContent(template.content);
    setResult(null);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setContent(String(ev.target?.result ?? ''));
      setFilePath(file.name);
      setResult(null);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const isYamlFile = /\.(ya?ml)$/i.test(filePath);

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader title={t('validation.title')} description={t('validation.subtitle')}>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !content.trim()}
            className="gap-2 shadow-lg shadow-primary/20"
            size="lg"
          >
            {mutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {mutation.isPending ? t('validation.running') : t('validation.runValidation')}
          </Button>
        </PageHeader>

        {mutation.isError && (
          <Alert variant="destructive">
            <AlertTitle>{t('validation.errorTitle')}</AlertTitle>
            <AlertDescription>{mutation.error.message}</AlertDescription>
          </Alert>
        )}

        {/* Templates */}
        <div className="flex flex-wrap items-center gap-2">
          {TEMPLATES.map((tpl) => (
            <Button key={tpl.id} variant="outline" size="sm" onClick={() => loadTemplate(tpl)} className="gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              {tpl.label}
            </Button>
          ))}
          <Link href="/yaml-editor">
            <Button variant="secondary" size="sm" className="gap-1.5">
              <FileCode2 className="h-3.5 w-3.5" />
              {t('validation.openYamlEditor')}
            </Button>
          </Link>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          {/* Editor */}
          <Card className="glass-card overflow-hidden">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Upload className="h-5 w-5 text-primary" />
                {t('validation.input')}
              </CardTitle>
              <CardDescription>{t('validation.inputDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="file-path">{t('validation.filePath')}</Label>
                <Input
                  id="file-path"
                  value={filePath}
                  onChange={(e) => setFilePath(e.target.value)}
                  placeholder="main.tf or deployment.yaml"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <input ref={fileInputRef} type="file" accept=".yaml,.yml,.tf,.tfvars,.hcl,.json" className="hidden" onChange={handleFileUpload} />
                <Button type="button" variant="secondary" size="sm" className="gap-1.5" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-3.5 w-3.5" />
                  {t('validation.upload')}
                </Button>
                <Button
                  type="button"
                  variant={includeAi ? 'default' : 'outline'}
                  size="sm"
                  className="gap-1.5"
                  onClick={() => setIncludeAi(!includeAi)}
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  AI {includeAi ? 'ON' : 'OFF'}
                </Button>
              </div>

              {isYamlFile ? (
                <YamlCodeEditor value={content} onChange={setContent} minHeight="360px" />
              ) : (
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="min-h-[360px]"
                  spellCheck={false}
                  aria-label="Code input"
                />
              )}
            </CardContent>
          </Card>

          {/* Results */}
          <Card className="glass-card overflow-hidden">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg">{t('validation.results')}</CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              {mutation.isPending && (
                <div className="flex min-h-[360px] flex-col items-center justify-center gap-4">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                    className="h-10 w-10 rounded-full border-2 border-primary border-t-transparent"
                  />
                  <p className="text-sm text-muted-foreground">{t('validation.analyzing')}</p>
                </div>
              )}

              {result && !mutation.isPending && <ValidationResults result={result} />}

              {!result && !mutation.isPending && (
                <div className="flex min-h-[360px] flex-col items-center justify-center text-center text-muted-foreground">
                  <FileText className="mb-3 h-12 w-12 opacity-30" />
                  <p>{t('validation.emptyResults')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* History */}
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
                  <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 p-4 transition-colors hover:bg-muted/30">
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
