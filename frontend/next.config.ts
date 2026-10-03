import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ensure Next.js uses src/ directory exclusively
  experimental: {},
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
