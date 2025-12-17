console.log('--- NEXT.CONFIG.JS LOADED ---');
console.log('Runtime Env Keys:', Object.keys(process.env).sort().join(', '));
console.log('MY_BACKEND_URL:', process.env.MY_BACKEND_URL);

/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        console.log('Rewrites called. MY_BACKEND_URL:', process.env.MY_BACKEND_URL);

        // TODO: Revert to env var once injection issue is resolved. Hardcoded for stability.
        const apiUrl = 'https://vinsight-backend-wddr2kfz3a-uc.a.run.app';
        // const backendUrl = process.env.MY_BACKEND_URL || process.env.API_URL;
        // const apiUrl = backendUrl ? backendUrl.trim() : 'http://localhost:8000';

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
