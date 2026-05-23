/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: [],
  experimental: {
    serverComponentsExternalPackages: [],
  },
};

module.exports = nextConfig;
