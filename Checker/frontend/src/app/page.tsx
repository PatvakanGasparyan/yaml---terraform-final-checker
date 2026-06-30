'use client';

import Link from 'next/link';
import { ArrowRight, Brain, FileCode, Shield, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AppShell } from '@/components/layout/app-shell';

const highlights = [
  {
    icon: FileCode,
    title: 'YAML & Terraform',
    description: 'Syntax, schema, Compose, Kubernetes, and HCL validation in one workspace.',
  },
  {
    icon: Shield,
    title: 'Security scanning',
    description: 'Surface misconfigurations and policy violations with severity classification.',
  },
  {
    icon: Brain,
    title: 'AI-assisted review',
    description: 'Optional line-by-line explanations and remediation suggestions.',
  },
];

export default function HomePage() {
  return (
    <AppShell>
      <section className="mx-auto max-w-4xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
          <Sparkles className="h-4 w-4" />
          Enterprise IaC validation platform
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          Validate infrastructure code{' '}
          <span className="bg-gradient-to-r from-primary to-cyan-500 bg-clip-text text-transparent">
            with confidence
          </span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          A professional web interface for the YAML & Terraform AI Validator API. Upload configurations,
          run validation, and review results in a clean, focused workspace.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/validate">
            <Button size="lg" className="h-12 gap-2 px-8">
              Open validator <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/docs">
            <Button size="lg" variant="outline" className="h-12 px-8">
              API documentation
            </Button>
          </Link>
        </div>
      </section>

      <section className="mx-auto mt-20 grid max-w-5xl gap-4 sm:grid-cols-3">
        {highlights.map((item) => (
          <div
            key={item.title}
            className="rounded-xl border border-border/80 bg-card/60 p-6 shadow-sm backdrop-blur-sm"
          >
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <item.icon className="h-5 w-5 text-primary" />
            </div>
            <h2 className="font-semibold">{item.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.description}</p>
          </div>
        ))}
      </section>
    </AppShell>
  );
}
