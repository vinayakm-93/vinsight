console.log('--- NEXT.CONFIG.JS LOADED ---');
console.log('Runtime Env Keys:', Object.keys(process.env).sort().join(', '));
console.log('MY_BACKEND_URL:', process.env.MY_BACKEND_URL);

/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        console.log('Rewrites called. MY_BACKEND_URL:', process.env.MY_BACKEND_URL);

        // Use Cloud Run backend URL for production
        const apiUrl = process.env.NODE_ENV === 'production'
            ? 'https://vinsight-backend-wddr2kfz3a-uc.a.run.app'
            : 'http://127.0.0.1:8000';

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
