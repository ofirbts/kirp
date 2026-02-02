/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  webpack(config) {
    if (process.env.ANALYZE === "true") {
      // When running `npm run analyze`, enable bundle analyzer
      // (relies on @next/bundle-analyzer if installed).
      try {
        // eslint-disable-next-line global-require, import/no-extraneous-dependencies
        const withBundleAnalyzer = require("@next/bundle-analyzer")({
          enabled: true,
        });
        return withBundleAnalyzer(config);
      } catch {
        // Analyzer not installed; fall back to default config.
        return config;
      }
    }
    return config;
  },
};

module.exports = nextConfig;
