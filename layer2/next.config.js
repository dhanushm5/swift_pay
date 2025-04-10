/** @type {import('next').NextConfig} */
const nextConfig = {
  // Removing output: 'export' to enable server-side rendering
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { unoptimized: true },
};

module.exports = nextConfig;
