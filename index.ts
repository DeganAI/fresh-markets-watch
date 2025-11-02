import { createAgentApp } from '@lucid-dreams/agent-kit';
import { Hono } from 'hono';

const PORT = parseInt(process.env.PORT || '3000', 10);
const FACILITATOR_URL = process.env.FACILITATOR_URL || 'https://facilitator.cdp.coinbase.com';
const WALLET_ADDRESS = process.env.ADDRESS || '0x01D11F7e1a46AbFC6092d7be484895D2d505095c';

interface FreshMarket {
  token_address: string;
  token_name: string;
  token_symbol: string;
  dex: string;
  chain_id: number;
  initial_liquidity_usd: number;
  price_usd: number;
  created_timestamp: string;
  age_hours: number;
}

async function fetchFreshMarkets(chainIds: number[], minLiquidity: number, maxAgeHours: number): Promise<FreshMarket[]> {
  // Simplified - in production would query Dexscreener/Birdeye
  const mockMarkets: FreshMarket[] = [
    {
      token_address: '0x1234567890abcdef1234567890abcdef12345678',
      token_name: 'New Token',
      token_symbol: 'NEW',
      dex: 'Uniswap V3',
      chain_id: 1,
      initial_liquidity_usd: 50000,
      price_usd: 0.05,
      created_timestamp: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
      age_hours: 2,
    },
  ];
  return mockMarkets.filter(m => chainIds.includes(m.chain_id) && m.initial_liquidity_usd >= minLiquidity && m.age_hours <= maxAgeHours);
}

const app = createAgentApp({
  name: 'Fresh Markets Watch',
  description: 'Spot newly listed tokens before they pump',
  version: '1.0.0',
  paymentsConfig: { facilitatorUrl: FACILITATOR_URL, address: WALLET_ADDRESS as `0x${string}`, network: 'base', defaultPrice: '$0.07' },
});

const honoApp = app.app;
honoApp.get('/health', (c) => c.json({ status: 'ok' }));
honoApp.get('/og-image.png', (c) => { c.header('Content-Type', 'image/svg+xml'); return c.body(`<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg"><rect width="1200" height="630" fill="#16213e"/><text x="600" y="315" font-family="Arial" font-size="60" fill="#4db6ac" text-anchor="middle" font-weight="bold">Fresh Markets Watch</text></svg>`); });

app.addEntrypoint({
  key: 'fresh-markets-watch',
  name: 'Fresh Markets Watch',
  description: 'Spot newly listed tokens',
  price: '$0.07',
  outputSchema: { input: { type: 'http', method: 'POST', discoverable: true, bodyType: 'json', bodyFields: { chain_ids: { type: 'array', required: true }, min_liquidity_usd: { type: 'number', required: true }, max_age_hours: { type: 'number', required: true } } }, output: { type: 'object', required: ['markets', 'timestamp'], properties: { markets: { type: 'array' }, total_found: { type: 'integer' }, timestamp: { type: 'string' } } } } as any,
  handler: async (ctx) => {
    const { chain_ids, min_liquidity_usd, max_age_hours } = ctx.input as any;
    const markets = await fetchFreshMarkets(chain_ids, min_liquidity_usd, max_age_hours);
    return { markets, total_found: markets.length, timestamp: new Date().toISOString() };
  },
});

const wrapperApp = new Hono();
wrapperApp.get('/favicon.ico', (c) => { c.header('Content-Type', 'image/svg+xml'); return c.body(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#4db6ac"/><text y=".9em" x="50%" text-anchor="middle" font-size="90">🆕</text></svg>`); });
wrapperApp.get('/', (c) => c.html(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Fresh Markets Watch</title><link rel="icon" type="image/svg+xml" href="/favicon.ico"><meta property="og:title" content="Fresh Markets Watch"><meta property="og:description" content="Spot newly listed tokens before they pump"><meta property="og:image" content="https://fresh-markets-watch-production.up.railway.app/og-image.png"><style>body{background:#16213e;color:#fff;font-family:system-ui;padding:40px}h1{color:#4db6ac}</style></head><body><h1>Fresh Markets Watch</h1><p>$0.07 USDC per request</p></body></html>`));
wrapperApp.all('*', async (c) => honoApp.fetch(c.req.raw));

if (typeof Bun !== 'undefined') { Bun.serve({ port: PORT, hostname: '0.0.0.0', fetch: wrapperApp.fetch }); } else { const { serve } = await import('@hono/node-server'); serve({ fetch: wrapperApp.fetch, port: PORT, hostname: '0.0.0.0' }); }
