import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveConfig } from 'vite';

async function configuration(command, apiUrl) {
  const original = process.env.VITE_API_BASE_URL;
  process.env.VITE_API_BASE_URL = apiUrl;
  try {
    return await resolveConfig({ logLevel: 'silent' }, command, 'production');
  } finally {
    if (original === undefined) delete process.env.VITE_API_BASE_URL;
    else process.env.VITE_API_BASE_URL = original;
  }
}

test('production builds reject missing or unreachable browser API configuration', async () => {
  for (const value of ['', 'http://127.0.0.1:8000', 'https://localhost:8000',
    'https://127.0.0.2:8000', 'https://[::1]:8000', 'https://0.0.0.0:8000',
    'http://api.example.com', '/api', 'not-a-url']) {
    await assert.rejects(configuration('build', value), /VITE_API_BASE_URL.*HTTPS.*backend/i,
      `Build accepted invalid production API URL: ${value}`);
  }
});

test('production builds accept an explicitly configured remote HTTPS backend', async () => {
  const config = await configuration('build', 'https://api.example.com');
  assert.equal(config.env.VITE_API_BASE_URL, 'https://api.example.com');
});

test('local development keeps the loopback API configuration', async () => {
  const config = await configuration('serve', 'http://127.0.0.1:8000');
  assert.equal(config.env.VITE_API_BASE_URL, 'http://127.0.0.1:8000');
});
