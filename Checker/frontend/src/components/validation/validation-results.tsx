'use client';

import { motion } from 'framer-motion';
import { AlertTriangle, Brain, CheckCircle2, Copy, Shield, Wrench } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import type { ValidationResult } from '@/lib/api';
import { SEVERITY_STYLES, STATUS_STYLES } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { useTranslations } from '@/hooks/use-translations';

interface ValidationResultsProps {
  result: ValidationResult;
}

export function ValidationResults({ result }: ValidationResultsProps) {
  const { t } = useTranslations();

  const copyCorrected = () => {
    if (result.corrected_content) {
      navigator.clipboard.writeText(result.corrected_content);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={cn('capitalize', STATUS_STYLES[result.status] ?? STATUS_STYLES.pending)}>
          {result.status}
        </Badge>
        <Badge variant="outline">{result.validation_type}</Badge>
        <span className="text-sm text-muted-foreground">{result.duration_ms}ms</span>
      </div>

      {result.summary && (
        <Alert variant={result.error_count > 0 ? 'destructive' : result.warning_count > 0 ? 'warning' : 'success'}>
          <AlertTitle>{t('validation.summary')}</AlertTitle>
          <AlertDescription>{result.summary}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {[
          { label: t('validation.errors'), value: result.error_count, color: 'text-red-500' },
          { label: t('validation.warnings'), value: result.warning_count, color: 'text-amber-500' },
          { label: t('validation.security'), value: result.security_findings_count, color: 'text-orange-500' },
          { label: t('validation.findings'), value: result.findings.length, color: 'text-primary' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-lg border bg-muted/30 p-3 text-center">
            <div className={cn('text-2xl font-bold', stat.color)}>{stat.value}</div>
            <div className="text-xs text-muted-foreground">{stat.label}</div>
          </div>
        ))}
      </div>

      <Tabs defaultValue="findings">
        <TabsList className="w-full flex-wrap h-auto gap-1">
          <TabsTrigger value="findings" className="gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5" />
            {t('validation.tabFindings')} ({result.findings.length})
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1.5">
            <Shield className="h-3.5 w-3.5" />
            {t('validation.tabSecurity')} ({result.security_findings?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="ai" className="gap-1.5">
            <Brain className="h-3.5 w-3.5" />
            {t('validation.tabAi')} ({result.ai_explanations?.length ?? 0})
          </TabsTrigger>
          {result.corrected_content && (
            <TabsTrigger value="fix" className="gap-1.5">
              <Wrench className="h-3.5 w-3.5" />
              {t('validation.tabFix')}
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="findings">
          <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
            {result.findings.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <CheckCircle2 className="mb-2 h-10 w-10 text-emerald-500" />
                <p>{t('validation.noFindings')}</p>
              </div>
            ) : (
              result.findings.map((finding, i) => (
                <motion.div
                  key={`${finding.message}-${i}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className={cn('rounded-lg border p-3 text-sm', SEVERITY_STYLES[finding.severity] ?? SEVERITY_STYLES.informational)}
                >
                  <div className="font-medium">
                    {finding.line_number != null && (
                      <span className="mr-2 rounded bg-background/50 px-1.5 py-0.5 font-mono text-xs">
                        L{finding.line_number}
                      </span>
                    )}
                    {finding.message}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs opacity-80">
                    <span>{finding.category}</span>
                    <span>•</span>
                    <span className="capitalize">{finding.severity}</span>
                  </div>
                  {finding.corrected_code && (
                    <pre className="mt-2 overflow-x-auto rounded bg-background/60 p-2 font-mono text-xs">
                      {finding.corrected_code}
                    </pre>
                  )}
                </motion.div>
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="security">
          <div className="max-h-[420px] space-y-2 overflow-y-auto">
            {(result.security_findings ?? []).length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">{t('validation.noSecurity')}</p>
            ) : (
              result.security_findings!.map((f, i) => (
                <div
                  key={`${f.rule_id}-${i}`}
                  className={cn('rounded-lg border p-3 text-sm', SEVERITY_STYLES[f.severity] ?? SEVERITY_STYLES.informational)}
                >
                  <div className="font-medium">{f.title}</div>
                  <div className="mt-1 text-xs opacity-80">
                    {f.scanner} • {f.rule_id}
                    {f.line_number != null && ` • Line ${f.line_number}`}
                  </div>
                  {f.remediation && <p className="mt-2 text-xs">{f.remediation}</p>}
                </div>
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="ai">
          <div className="max-h-[420px] space-y-2 overflow-y-auto">
            {(result.ai_explanations ?? []).length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">{t('validation.noAi')}</p>
            ) : (
              result.ai_explanations!.map((exp) => (
                <div key={exp.line_number} className="rounded-lg border bg-muted/20 p-3 text-sm">
                  <div className="mb-1 flex items-center gap-2">
                    <Badge variant="outline" className="font-mono text-xs">
                      L{exp.line_number}
                    </Badge>
                    <Badge variant="outline" className="capitalize text-xs">
                      {exp.risk_level}
                    </Badge>
                  </div>
                  <pre className="mb-2 overflow-x-auto rounded bg-background/60 p-2 font-mono text-xs">{exp.code}</pre>
                  <p>{exp.explanation}</p>
                  {exp.recommendation && (
                    <p className="mt-2 text-xs text-primary">{exp.recommendation}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </TabsContent>

        {result.corrected_content && (
          <TabsContent value="fix">
            <div className="relative">
              <Button size="sm" variant="outline" className="absolute right-2 top-2 gap-1" onClick={copyCorrected}>
                <Copy className="h-3.5 w-3.5" /> {t('validation.copy')}
              </Button>
              <pre className="max-h-[420px] overflow-auto rounded-lg border bg-muted/30 p-4 pt-12 font-mono text-xs leading-relaxed">
                {result.corrected_content}
              </pre>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
