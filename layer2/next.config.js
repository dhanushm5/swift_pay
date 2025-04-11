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
    // Increase chunk loading timeout to 60 seconds
    incrementalCacheHandlerPath: false,
    isrMemoryCacheSize: 0,
    timeoutAttempts: 3
  },
};

module.exports = nextConfig;
