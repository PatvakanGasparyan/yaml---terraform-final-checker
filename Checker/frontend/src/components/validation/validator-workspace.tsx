'use client';

import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Loader2, Play, Sparkles, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ValidationResults } from '@/components/validation/validation-results';
import { YamlCodeEditor } from '@/components/yaml/yaml-code-editor';
import { api, type ValidationResult } from '@/lib/api';
import { SAMPLE_TERRAFORM, SAMPLE_YAML, TEMPLATES } from '@/lib/constants';
import { cn } from '@/lib/utils';

export type ValidationType = 'auto' | 'yaml' | 'terraform';

const TYPE_OPTIONS: { value: ValidationType; label: string; description: string }[] = [
  { value: 'auto', label: 'Auto-detect', description: 'Infer from file extension' },
  { value: 'yaml', label: 'YAML', description: 'Kubernetes, Compose, CI/CD' },
  { value: 'terraform', label: 'Terraform', description: 'HCL / .tf configurations' },
];

export interface ValidatorWorkspaceProps {
  /** Show quick-load template chips above the editor */
  showTemplates?: boolean;
  className?: string;
  /** Called after a successful validation (e.g. refresh history) */
  onValidated?: (result: ValidationResult) => void;
}

export function ValidatorWorkspace({ showTemplates = true, className, onValidated }: ValidatorWorkspaceProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [content, setContent] = useState(SAMPLE_YAML);
  const [filePath, setFilePath] = useState('deployment.yaml');
  const [validationType, setValidationType] = useState<ValidationType>('auto');
  const [includeAi, setIncludeAi] = useState(true);
  const [result, setResult] = useState<ValidationResult | null>(null);

  const isYamlFile = /\.(ya?ml)$/i.test(filePath);

  const mutation = useMutation({
    mutationFn: () =>
      api.post<ValidationResult>('/validations/run', {
        content,
        file_path: filePath,
        validation_type: validationType,
        include_ai_analysis: includeAi,
        include_security_scan: true,
      }),
    onSuccess: (data) => {
      setResult(data);
      onValidated?.(data);
    },
  });

  const loadTemplate = (template: (typeof TEMPLATES)[number]) => {
    setFilePath(template.path);
    setContent(template.content);
    setValidationType(template.type === 'terraform' ? 'terraform' : 'yaml');
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

  return (
    <div className={cn('space-y-6', className)}>
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input */}
        <Card className="border-border/80 shadow-sm">
          <CardHeader className="border-b bg-muted/30 pb-4">
            <CardTitle className="text-lg font-semibold">Configuration input</CardTitle>
            <CardDescription>
              Paste or upload YAML / Terraform. Click <strong>Validate</strong> to run analysis via the API.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="validation-type">Type</Label>
                <select
                  id="validation-type"
                  value={validationType}
                  onChange={(e) => setValidationType(e.target.value as ValidationType)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="file-path">File path</Label>
                <Input
                  id="file-path"
                  value={filePath}
                  onChange={(e) => setFilePath(e.target.value)}
                  placeholder="main.tf or deployment.yaml"
                />
              </div>
            </div>

            {showTemplates && (
              <div className="flex flex-wrap gap-2">
                {TEMPLATES.map((tpl) => (
                  <Button
                    key={tpl.id}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => loadTemplate(tpl)}
                  >
                    {tpl.label}
                  </Button>
                ))}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".yaml,.yml,.tf,.tfvars,.hcl,.json"
                className="hidden"
                onChange={handleFileUpload}
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="gap-1.5"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-3.5 w-3.5" />
                Upload file
              </Button>
              <Button
                type="button"
                variant={includeAi ? 'default' : 'outline'}
                size="sm"
                className="gap-1.5"
                onClick={() => setIncludeAi((v) => !v)}
              >
                <Sparkles className="h-3.5 w-3.5" />
                AI analysis {includeAi ? 'on' : 'off'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setContent(SAMPLE_TERRAFORM);
                  setFilePath('main.tf');
                  setValidationType('terraform');
                  setResult(null);
                }}
              >
                Load Terraform sample
              </Button>
            </div>

            {isYamlFile ? (
              <YamlCodeEditor value={content} onChange={setContent} minHeight="320px" />
            ) : (
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="min-h-[320px] font-mono text-sm leading-relaxed"
                spellCheck={false}
                aria-label="Configuration content"
                placeholder="# Paste YAML or Terraform here…"
              />
            )}

            <Button
              type="button"
              size="lg"
              className="w-full gap-2 sm:w-auto"
              disabled={mutation.isPending || !content.trim()}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {mutation.isPending ? 'Validating…' : 'Validate'}
            </Button>
          </CardContent>
        </Card>

        {/* Output */}
        <Card className="border-border/80 shadow-sm">
          <CardHeader className="border-b bg-muted/30 pb-4">
            <CardTitle className="text-lg font-semibold">Results</CardTitle>
            <CardDescription>
              Validation findings, security issues, and AI explanations from{' '}
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">POST /api/v1/validations/run</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5">
            {mutation.isError && (
              <Alert variant="destructive" className="mb-4">
                <AlertTitle>Validation failed</AlertTitle>
                <AlertDescription>{mutation.error.message}</AlertDescription>
              </Alert>
            )}

            {mutation.isPending && (
              <div className="flex min-h-[360px] flex-col items-center justify-center gap-3 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm">Running validators and security checks…</p>
              </div>
            )}

            {result && !mutation.isPending && <ValidationResults result={result} />}

            {!result && !mutation.isPending && !mutation.isError && (
              <div className="flex min-h-[360px] flex-col items-center justify-center rounded-lg border border-dashed bg-muted/20 px-6 text-center text-muted-foreground">
                <p className="text-sm">Submit a configuration to see errors, warnings, security findings, and AI analysis.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
