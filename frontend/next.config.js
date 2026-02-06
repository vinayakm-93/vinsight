console.log('--- NEXT.CONFIG.JS LOADED ---');
console.log('Runtime Env Keys:', Object.keys(process.env).sort().join(', '));
console.log('MY_BACKEND_URL:', process.env.MY_BACKEND_URL);

/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        console.log('Rewrites called. MY_BACKEND_URL:', process.env.MY_BACKEND_URL);

        // Use MY_BACKEND_URL if set, otherwise fallback to localhost for dev
        const apiUrl = process.env.NODE_ENV === 'production'
            ? process.env.MY_BACKEND_URL
            : 'http://127.0.0.1:8000';

        if (process.env.NODE_ENV === 'production' && !apiUrl) {
            console.error('FATAL: MY_BACKEND_URL is not set in production environment!');
            // In a real build this would fail, but for now we log it.
        }

        console.log('Proxying /api requests to:', apiUrl);

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
