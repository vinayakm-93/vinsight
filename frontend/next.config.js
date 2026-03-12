/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        // Use explicit backend URL in production and a local default in development.
        const apiUrl = process.env.NODE_ENV === 'production'
            ? process.env.MY_BACKEND_URL
            : process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

        if (process.env.NODE_ENV === 'production' && !apiUrl) {
            throw new Error('MY_BACKEND_URL is required in production environment.');
        }

        return [
            {
                source: '/api/:path*',
                destination: `${apiUrl}/api/:path*`,
            },
            {
                source: '/docs',
                destination: `${apiUrl}/docs`,
            },
            {
                source: '/openapi.json',
                destination: `${apiUrl}/openapi.json`,
            },
        ];
    },
};

module.exports = nextConfig;
