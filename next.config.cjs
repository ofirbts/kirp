const { PHASE_PRODUCTION_BUILD } = require("next/constants");

/**
 * Standalone output must apply only during `next build`, not during `next dev`.
 * Otherwise a mixed `.next` (production trace + dev server) often yields 404 on
 * `/_next/static/chunks/main-app.js`, `layout.css`, etc., while `webpack.js` still returns 200.
 *
 * @type {(phase: string) => import('next').NextConfig}
 */
module.exports = (phase) => {
  /** @type {import('next').NextConfig} */
  const nextConfig = {
    reactStrictMode: true,
    webpack(config) {
      if (process.env.ANALYZE === "true") {
        try {
          // eslint-disable-next-line global-require, import/no-extraneous-dependencies
          const withBundleAnalyzer = require("@next/bundle-analyzer")({
            enabled: true,
          });
          return withBundleAnalyzer(config);
        } catch {
          return config;
        }
      }
      return config;
    },
  };

  if (phase === PHASE_PRODUCTION_BUILD) {
    nextConfig.output = "standalone";
  }

  return nextConfig;
};
