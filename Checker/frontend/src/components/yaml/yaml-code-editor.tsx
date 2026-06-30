'use client';

import { useCallback, useEffect, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { yaml } from '@codemirror/lang-yaml';
import { oneDark } from '@codemirror/theme-one-dark';
import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';

interface YamlCodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  minHeight?: string;
  readOnly?: boolean;
  'aria-label'?: string;
}

export function YamlCodeEditor({
  value,
  onChange,
  className,
  minHeight = '420px',
  readOnly = false,
  'aria-label': ariaLabel = 'YAML editor',
}: YamlCodeEditorProps) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const handleChange = useCallback(
    (val: string) => {
      onChange(val);
    },
    [onChange]
  );

  if (!mounted) {
    return (
      <div
        className={cn('animate-pulse rounded-lg border bg-muted/40', className)}
        style={{ minHeight }}
        aria-hidden
      />
    );
  }

  return (
    <div className={cn('overflow-hidden rounded-lg border border-border/80 shadow-inner', className)}>
      <CodeMirror
        value={value}
        height={minHeight}
        theme={resolvedTheme === 'dark' ? oneDark : 'light'}
        extensions={[yaml()]}
        onChange={handleChange}
        readOnly={readOnly}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLineGutter: true,
          highlightActiveLine: true,
          foldGutter: true,
          indentOnInput: true,
          tabSize: 2,
        }}
        aria-label={ariaLabel}
        className="text-sm [&_.cm-editor]:outline-none [&_.cm-scroller]:font-mono"
      />
    </div>
  );
}
