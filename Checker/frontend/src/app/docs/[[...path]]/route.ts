import { NextRequest, NextResponse } from 'next/server';

import { API_URL } from '@/lib/env';

const backendUrl = API_URL;

type RouteContext = { params: Promise<{ path?: string[] }> };

async function proxyDocs(req: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { path } = await context.params;
  const suffix = path?.length ? `/${path.join('/')}` : '';
  const target = `${backendUrl}/docs${suffix}${req.nextUrl.search}`;

  const response = await fetch(target, {
    method: req.method,
    headers: { accept: req.headers.get('accept') ?? '*/*' },
    redirect: 'manual',
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete('content-encoding');

  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export async function GET(req: NextRequest, context: RouteContext) {
  return proxyDocs(req, context);
}
