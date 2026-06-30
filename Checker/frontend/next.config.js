/** @type {import('next').NextConfig} */
// Server-side rewrites (Docker) use internal service URL; browser uses relative /api/v1
const backendUrl =
  process.env.API_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000';

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'avatars.githubusercontent.com' },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
      {
        source: '/docs',
        destination: `${backendUrl}/docs`,
      },
      {
        source: '/docs/:path*',
        destination: `${backendUrl}/docs/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
