'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useMutation } from '@tanstack/react-query';
import {
  AlignLeft,
  AlertCircle,
  CheckCircle2,
  Download,
  FileUp,
  Loader2,
  Play,
  RotateCcw,
  Save,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { PageHeader } from '@/components/layout/page-header';
import { YamlCodeEditor } from '@/components/yaml/yaml-code-editor';
import { ValidationResults } from '@/components/validation/validation-results';
import { api, type ValidationResult } from '@/lib/api';
import { SAMPLE_YAML } from '@/lib/constants';
import {
  downloadYaml,
  formatYaml,
  validateYaml,
  YAML_DRAFT_KEY,
  YAML_FILENAME_KEY,
} from '@/lib/yaml-utils';
import { useTranslations } from '@/hooks/use-translations';
import { cn } from '@/lib/utils';

export default function YamlEditorPage() {
  const { t } = useTranslations();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [content, setContent] = useState(SAMPLE_YAML);
  const [filename, setFilename] = useState('config.yaml');
  const [formatError, setFormatError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  const yamlCheck = useMemo(() => validateYaml(content), [content]);

  useEffect(() => {
    try {
      const draft = localStorage.getItem(YAML_DRAFT_KEY);
      const savedName = localStorage.getItem(YAML_FILENAME_KEY);
      if (draft) setContent(draft);
      if (savedName) setFilename(savedName);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(YAML_DRAFT_KEY, content);
        localStorage.setItem(YAML_FILENAME_KEY, filename);
      } catch {
        /* ignore */
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [content, filename]);

  const handleFormat = useCallback(() => {
    try {
      setContent(formatYaml(content));
      setFormatError(null);
    } catch (err) {
      setFormatError(err instanceof Error ? err.message : 'Invalid YAML');
    }
  }, [content]);

  const handleLoadFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setContent(String(ev.target?.result ?? ''));
      setFilename(file.name);
      setFormatError(null);
      setValidationResult(null);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleSaveDraft = () => {
    try {
      localStorage.setItem(YAML_DRAFT_KEY, content);
      localStorage.setItem(YAML_FILENAME_KEY, filename);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const handleReset = () => {
    setContent(SAMPLE_YAML);
    setFilename('config.yaml');
    setFormatError(null);
    setValidationResult(null);
  };

  const validateMutation = useMutation({
    mutationFn: () =>
      api.post<ValidationResult>('/validations/run', {
        content,
        file_path: filename,
        validation_type: 'yaml',
        include_ai_analysis: true,
        include_security_scan: true,
      }),
    onSuccess: (data) => setValidationResult(data),
  });

  const canRunValidation = yamlCheck.valid && content.trim().length > 0;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader title={t('yamlEditor.title')} description={t('yamlEditor.subtitle')}>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleFormat}
              disabled={!content.trim()}
            >
              <AlignLeft className="h-4 w-4" />
              {t('yamlEditor.format')}
            </Button>
            <Button
              size="lg"
              className="gap-2 shadow-lg shadow-primary/20"
              disabled={!canRunValidation || validateMutation.isPending}
              onClick={() => validateMutation.mutate()}
            >
              {validateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {validateMutation.isPending ? t('validation.running') : t('yamlEditor.runValidation')}
            </Button>
          </div>
        </PageHeader>

        {formatError && (
          <Alert variant="destructive">
            <AlertTitle>{t('yamlEditor.syntaxError')}</AlertTitle>
            <AlertDescription>{formatError}</AlertDescription>
          </Alert>
        )}

        {validateMutation.isError && (
          <Alert variant="destructive">
            <AlertTitle>{t('validation.errorTitle')}</AlertTitle>
            <AlertDescription>{validateMutation.error.message}</AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 xl:grid-cols-5">
          <div className="space-y-4 xl:col-span-3">
            <Card className="glass-card overflow-hidden">
              <CardHeader className="border-b bg-muted/20">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-lg">{t('yamlEditor.editor')}</CardTitle>
                    <CardDescription>{t('yamlEditor.editorDesc')}</CardDescription>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      'gap-1.5',
                      yamlCheck.valid
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                        : 'border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400'
                    )}
                  >
                    {yamlCheck.valid ? (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    ) : (
                      <AlertCircle className="h-3.5 w-3.5" />
                    )}
                    {yamlCheck.valid ? t('yamlEditor.valid') : t('yamlEditor.invalid')}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="yaml-filename">{t('yamlEditor.filename')}</Label>
                  <Input
                    id="yaml-filename"
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    placeholder="deployment.yaml"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".yaml,.yml"
                    className="hidden"
                    onChange={handleLoadFile}
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <FileUp className="h-3.5 w-3.5" />
                    {t('yamlEditor.load')}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => downloadYaml(content, filename)}
                    disabled={!content.trim()}
                  >
                    <Download className="h-3.5 w-3.5" />
                    {t('yamlEditor.export')}
                  </Button>
                  <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={handleSaveDraft}>
                    <Save className="h-3.5 w-3.5" />
                    {saved ? t('yamlEditor.saved') : t('yamlEditor.saveDraft')}
                  </Button>
                  <Button type="button" variant="ghost" size="sm" className="gap-1.5" onClick={handleReset}>
                    <RotateCcw className="h-3.5 w-3.5" />
                    {t('yamlEditor.reset')}
                  </Button>
                </div>

                <YamlCodeEditor value={content} onChange={setContent} minHeight="480px" />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4 xl:col-span-2">
            {!yamlCheck.valid && (
              <Card className="glass-card border-red-500/30">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base text-red-600 dark:text-red-400">
                    <AlertCircle className="h-4 w-4" />
                    {t('yamlEditor.errors')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm">
                    {yamlCheck.errors.map((err, i) => (
                      <li key={i} className="rounded-md bg-red-500/5 px-3 py-2 font-mono text-red-700 dark:text-red-300">
                        <span className="text-muted-foreground">Line {err.line}:</span> {err.message}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-lg">{t('yamlEditor.tips')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>{t('yamlEditor.tip1')}</p>
                <p>{t('yamlEditor.tip2')}</p>
                <Link href="/validations" className="inline-block text-primary hover:underline">
                  {t('yamlEditor.goValidations')} →
                </Link>
              </CardContent>
            </Card>

            {validationResult && (
              <Card className="glass-card overflow-hidden">
                <CardHeader className="border-b bg-muted/20">
                  <CardTitle className="text-lg">{t('validation.results')}</CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <ValidationResults result={validationResult} />
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
