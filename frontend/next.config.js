/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',       // static export — deploys to Vercel / GitHub Pages with no server
  trailingSlash: true,    // needed for static export routing
  experimental: {
    optimizePackageImports: ['recharts'],
  },
}

module.exports = nextConfig
