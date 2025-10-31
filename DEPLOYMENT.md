# Deployment Guide

## Quick Deploy to Railway

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
```

2. **Login:**
```bash
railway login
```

3. **Initialize project:**
```bash
railway init
```

4. **Set environment variables:**
```bash
railway variables set PAYMENT_ADDRESS=0xYourAddress
railway variables set ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
railway variables set BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
railway variables set ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
railway variables set FREE_MODE=false
railway variables set SUPPORTED_CHAINS=ethereum,base,arbitrum
```

5. **Deploy:**
```bash
railway up
```

6. **Get your URL:**
```bash
railway domain
```

## Environment Variables Required

### Essential
- `PAYMENT_ADDRESS` - Your Ethereum address for receiving payments
- `ETHEREUM_RPC_URL` - Ethereum RPC endpoint
- `FREE_MODE` - Set to "true" for testing, "false" for production

### Optional but Recommended
- `BASE_RPC_URL` - Base chain RPC endpoint
- `ARBITRUM_RPC_URL` - Arbitrum RPC endpoint
- `ETHEREUM_EXPLORER_API_KEY` - Etherscan API key
- `BASE_EXPLORER_API_KEY` - Basescan API key
- `ARBITRUM_EXPLORER_API_KEY` - Arbiscan API key
- `PORT` - Server port (default: 8000)
- `SUPPORTED_CHAINS` - Comma-separated chain list

## RPC Providers

### Recommended Providers
- **Alchemy** (recommended): https://www.alchemy.com/
- **Infura**: https://www.infura.io/
- **QuickNode**: https://www.quicknode.com/

### Getting RPC URLs

1. Sign up for an account
2. Create a new app/project
3. Select the chain (Ethereum, Base, Arbitrum)
4. Copy the HTTP endpoint URL

Example Alchemy URL format:
```
https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

## Block Explorer API Keys

Get free API keys from:
- Ethereum: https://etherscan.io/apis
- Base: https://basescan.org/apis
- Arbitrum: https://arbiscan.io/apis

These are optional but enable holder analysis.

## Production Checklist

- [ ] Set `FREE_MODE=false`
- [ ] Configure `PAYMENT_ADDRESS` with your Ethereum address
- [ ] Add RPC URLs for all chains you want to support
- [ ] Add block explorer API keys (optional)
- [ ] Test health endpoint: `curl https://your-domain.com/health`
- [ ] Test payment flow with small USDC transaction
- [ ] Monitor logs for errors
- [ ] Set up monitoring/alerting

## Testing Deployment

```bash
# Test health
curl https://your-domain.com/health

# Test info
curl https://your-domain.com/info

# Test scan (with payment)
curl -X POST https://your-domain.com/scan \
  -H "Content-Type: application/json" \
  -H "X-Payment-TxHash: 0xYourTxHash" \
  -d '{"chain": "ethereum", "window_minutes": 5}'
```

## Monitoring

Check logs on Railway:
```bash
railway logs
```

Or in Railway dashboard: https://railway.app/dashboard

## Troubleshooting

### "Failed to connect to RPC"
- Check RPC URL is correct
- Verify API key is valid
- Check rate limits

### "Payment verification failed"
- Ensure USDC amount >= 0.05
- Transaction must be confirmed
- Transaction must be within 1 hour
- Check correct payment address

### "No pairs found"
- Increase window_minutes
- Check chain is synced
- Verify factory addresses

## Cost Estimates

### Railway
- Free tier: 500 hours/month
- Starter plan: $5/month
- Estimated cost: $5-20/month depending on usage

### RPC Costs
- Alchemy free tier: 300M compute units/month
- Usually sufficient for moderate usage
- Monitor usage in provider dashboard

### Revenue Potential
- $0.05 per API call
- Break even: 100-400 requests/month
- Profitable above break-even point
