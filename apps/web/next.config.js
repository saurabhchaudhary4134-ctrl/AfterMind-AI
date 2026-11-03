/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Docker standalone image (infra/docker/web.Dockerfile).
  // Vercel ignores this setting and handles output automatically.
  output: "standalone",
};

module.exports = nextConfig;
