export const SAMPLE_YAML = `apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:latest
    ports:
    - containerPort: 80
    securityContext:
      privileged: true
      runAsUser: 0
`;

export const SAMPLE_TERRAFORM = `terraform {
  required_version = ">= 1.0"
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "logs" {
  bucket = "my-app-logs"
  acl    = "public-read"
}

resource "aws_security_group" "web" {
  name = "web-sg"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
`;

export const SAMPLE_COMPOSE = `services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      API_KEY: "sk-hardcoded-secret-key-12345"
`;

export const TEMPLATES = [
  { id: 'yaml-k8s', label: 'Kubernetes Pod', path: 'deployment.yaml', content: SAMPLE_YAML, type: 'yaml' },
  { id: 'terraform', label: 'Terraform AWS', path: 'main.tf', content: SAMPLE_TERRAFORM, type: 'terraform' },
  { id: 'compose', label: 'Docker Compose', path: 'docker-compose.yaml', content: SAMPLE_COMPOSE, type: 'yaml' },
] as const;

export const SEVERITY_STYLES: Record<string, string> = {
  critical: 'border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-300',
  high: 'border-orange-500/50 bg-orange-500/10 text-orange-700 dark:text-orange-300',
  medium: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-800 dark:text-yellow-300',
  low: 'border-blue-500/50 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  informational: 'border-border bg-muted/50 text-muted-foreground',
};

export const STATUS_STYLES: Record<string, string> = {
  success: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  failed: 'bg-red-500/15 text-red-700 dark:text-red-300',
  warning: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  running: 'bg-blue-500/15 text-blue-700 dark:text-blue-300',
  pending: 'bg-muted text-muted-foreground',
};
