/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable static exports
  output: 'standalone',
  // Disable the new app router for now as it's experimental
  experimental: {
    // For Next.js 15 compatibility
  },
  // This is crucial for Docker - tell Next.js to listen on all interfaces (0.0.0.0)
  // instead of just localhost
  async rewrites() {
    return [];
  }
};

export default nextConfig; 