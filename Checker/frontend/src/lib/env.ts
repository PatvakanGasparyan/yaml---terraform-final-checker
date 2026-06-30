/**
 * Runtime configuration loaded exclusively from the .env file.
 * In Docker, docker-entrypoint.sh sources /app/.env into process.env before Node starts.
 */

function readEnv(key: string, fallback = ''): string {
  const value = process.env[key];
  return value !== undefined && value !== '' ? value : fallback;
}

export const API_INTERNAL_URL = readEnv('API_INTERNAL_URL', 'http://backend:8000');
export const NEXT_PUBLIC_API_URL = readEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
export const API_URL = API_INTERNAL_URL || NEXT_PUBLIC_API_URL;
