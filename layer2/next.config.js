/** @type {import('next').NextConfig} */
const nextConfig = {
  // Removing output: 'export' to enable server-side rendering
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { unoptimized: true },
  webpack: (config) => {
    config.watchOptions = {
      ...config.watchOptions,
      poll: 1000,
    };
    return config;
  },
  experimental: {
    // Add any currently supported experimental features here if needed
  },
};

module.exports = nextConfig;
