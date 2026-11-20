import { mkdirSync, writeFileSync } from 'node:fs';

const adminUrl = 'https://store-api.143-244-168-180.sslip.io/control/';
const redirect = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<title>RODDY Staff Sign-in</title>
<script>location.replace(${JSON.stringify(adminUrl)} + location.hash);</script>
</head>
<body><main><a href="${adminUrl}">Open RODDY staff sign-in</a></main></body>
</html>
`;

mkdirSync('dist/admin', { recursive: true });
writeFileSync('dist/admin.html', redirect);
writeFileSync('dist/admin/index.html', redirect);
