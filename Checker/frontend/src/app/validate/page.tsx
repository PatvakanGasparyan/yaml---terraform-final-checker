'use client';

import { ValidatorWorkspace } from '@/components/validation/validator-workspace';
import { AppShell } from '@/components/layout/app-shell';

export default function ValidatePage() {
  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Configuration validator</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Validate YAML and Terraform in real time. Results include syntax checks, security findings, and optional AI analysis.
          </p>
        </div>
        <ValidatorWorkspace />
      </div>
    </AppShell>
  );
}
