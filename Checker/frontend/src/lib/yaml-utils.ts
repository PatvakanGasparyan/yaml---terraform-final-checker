import { parseDocument, LineCounter } from 'yaml';

export interface YamlValidationResult {
  valid: boolean;
  errors: { line: number; message: string }[];
}

export function validateYaml(content: string): YamlValidationResult {
  if (!content.trim()) {
    return { valid: true, errors: [] };
  }

  const lineCounter = new LineCounter();
  const doc = parseDocument(content, { lineCounter, prettyErrors: false });

  if (!doc.errors.length) {
    return { valid: true, errors: [] };
  }

  return {
    valid: false,
    errors: doc.errors.map((err) => ({
      line: lineCounter.linePos(err.pos[0]).line,
      message: err.message.replace(/\n/g, ' '),
    })),
  };
}

export function formatYaml(content: string): string {
  const doc = parseDocument(content);
  if (doc.errors.length) {
    throw new Error(doc.errors[0].message);
  }
  return String(doc);
}

export function downloadYaml(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/yaml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename.endsWith('.yaml') || filename.endsWith('.yml') ? filename : `${filename}.yaml`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const YAML_DRAFT_KEY = 'ytv-yaml-editor-draft';
export const YAML_FILENAME_KEY = 'ytv-yaml-editor-filename';
