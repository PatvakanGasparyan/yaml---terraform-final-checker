'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Shield, GitBranch, Brain, Sparkles, FileCode, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslations } from '@/hooks/use-translations';

const features = [
  { icon: Shield, titleKey: 'landing.featureSecurity', descKey: 'landing.featureSecurityDesc' },
  { icon: FileCode, titleKey: 'landing.featureYaml', descKey: 'landing.featureYamlDesc' },
  { icon: Brain, titleKey: 'landing.featureAi', descKey: 'landing.featureAiDesc' },
  { icon: GitBranch, titleKey: 'landing.featureGithub', descKey: 'landing.featureGithubDesc' },
  { icon: Lock, titleKey: 'landing.featureScan', descKey: 'landing.featureScanDesc' },
  { icon: Sparkles, titleKey: 'landing.featureInstant', descKey: 'landing.featureInstantDesc' },
];

export default function HomePage() {
  const { t } = useTranslations();

  return (
    <div className="min-h-screen">
      <header className="container mx-auto flex items-center justify-between px-4 py-5 sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <span className="text-lg font-bold sm:text-xl">{t('common.appName')}</span>
        </div>
        <Link href="/validations">
          <Button className="gap-2 shadow-lg shadow-primary/20">
            {t('landing.startNow')} <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </header>

      <main className="container mx-auto px-4 pb-20 pt-8 sm:px-6 sm:pt-16">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-4xl text-center"
        >
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
            <Sparkles className="h-4 w-4" />
            {t('landing.badge')}
          </div>
          <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
            {t('landing.title1')}{' '}
            <span className="gradient-text">{t('landing.title2')}</span>
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground sm:text-xl">
            {t('landing.subtitle')}
          </p>
          <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/validations">
              <Button size="lg" className="h-12 gap-2 px-8 text-base shadow-lg shadow-primary/25">
                {t('landing.ctaValidate')} <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="h-12 px-8 text-base">
                {t('landing.ctaDashboard')}
              </Button>
            </Link>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="mt-20 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature, i) => (
            <motion.div
              key={feature.titleKey}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              className="glass-card group p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/5"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 transition-colors group-hover:bg-primary/20">
                <feature.icon className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-lg font-semibold">{t(feature.titleKey)}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{t(feature.descKey)}</p>
            </motion.div>
          ))}
        </motion.div>
      </main>
    </div>
  );
}
