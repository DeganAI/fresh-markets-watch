# Fresh Markets Watch

Real-time AMM pair monitoring for discovery bots and yield scouts.

## Overview

Fresh Markets Watch monitors AMM factory contracts across multiple chains to detect newly created pairs and pools within 60 seconds of creation. Perfect for discovering early opportunities in emerging markets.

## Features

- **Real-Time Detection**: Detect new pairs within 60 seconds with <1% false positive rate
- **Multi-DEX Support**: Monitor Uniswap V2/V3, SushiSwap, PancakeSwap, QuickSwap, and more
- **Complete Data**: Get pair address, tokens, initial liquidity, top holders, and creation timestamp
- **7 Chains**: Ethereum, Polygon, Arbitrum, Optimism, Base, BNB Chain, Avalanche

## Supported AMMs

- Uniswap V2 & V3
- SushiSwap
- PancakeSwap
- QuickSwap
- TraderJoe

## API Endpoints

### POST /markets/new

Discover new pairs created in the specified time window.

**Request:**
```json
{
  "chain": 1,
  "factories": ["0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"],
  "window_minutes": 5
}
```

**Response:**
```json
{
  "pairs": [{
    "pair_address": "0x...",
    "tokens": ["0x...", "0x..."],
    "token_symbols": ["WETH", "USDC"],
    "init_liquidity": "125000.50",
    "top_holders": ["0x...", "0x..."],
    "created_at": "2025-10-31T18:30:00Z",
    "factory": "0x5C69...",
    "block_number": 12345678
  }],
  "total": 12,
  "scanned_blocks": 100,
  "timestamp": "2025-10-31T18:35:00Z"
}
```

### GET /chains

List all supported blockchain networks.

### GET /factories/{chain_id}

Get known factory addresses for a specific chain.

### GET /health

Health check endpoint.

## Development

### Local Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Run the server:
   ```bash
   uvicorn src.main:app --reload
   ```

### Environment Variables

- `PORT`: Server port (default: 8000)
- `FREE_MODE`: Set to `true` for free mode, `false` for payment verification
- `PAYMENT_ADDRESS`: Payment wallet address
- `BASE_URL`: Service base URL
- RPC URLs for each chain

## Deployment

### Railway

1. Push to GitHub
2. Connect repository to Railway
3. Set environment variables
4. Deploy

Railway will automatically:
- Build the Docker image
- Start the service
- Handle health checks
- Manage restarts

## x402 Payment Protocol

This service uses the x402 payment protocol for usage-based billing:

- **Price**: 0.05 USDC per request
- **Network**: Base
- **Payment Address**: `0x01D11F7e1a46AbFC6092d7be484895D2d505095c`
- **Facilitator**: https://facilitator.daydreams.systems

## Technical Details

### Event Monitoring

The service monitors PairCreated events from Uniswap V2-style factories and PoolCreated events from Uniswap V3 factories. It calculates block ranges based on the time window and scans for events within that range.

### Liquidity Tracking

Initial liquidity is calculated by querying the pair's reserves and multiplying by token prices from CoinGecko.

### Holder Analysis

Top holders are determined by analyzing Transfer events from the pair contract and aggregating balances.

## License

MIT

## Built By

DeganAI - Bounty #1 Submission for Daydreams AI Agent Bounties
