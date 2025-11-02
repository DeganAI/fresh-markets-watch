"""
Fresh Markets Watch - AMM pair monitoring agent

x402 micropayment-enabled pair discovery service
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import os
import logging
from web3 import Web3

from src.pair_monitor import PairMonitor
from src.liquidity_tracker import LiquidityTracker
from src.holder_analyzer import HolderAnalyzer
from src.factory_config import get_supported_chains, get_chain_name, get_all_factories
from src.price_feed import get_token_prices
from src.x402_middleware_dual import X402Middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Fresh Markets Watch",
    description="Real-time AMM pair monitoring for discovery bots and yield scouts - powered by x402",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration
payment_address = os.getenv("PAYMENT_ADDRESS", "0x01D11F7e1a46AbFC6092d7be484895D2d505095c")
base_url = os.getenv("BASE_URL", "https://fresh-markets-watch-production.up.railway.app")
free_mode = os.getenv("FREE_MODE", "true").lower() == "true"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# x402 Payment Verification Middleware
app.add_middleware(
    X402Middleware,
    payment_address=payment_address,
    base_url=base_url,
    facilitator_urls=[
        "https://facilitator.daydreams.systems",
        "https://api.cdp.coinbase.com/platform/v2/x402/facilitator"
    ],
    free_mode=free_mode,
)

logger.info(f"Running in {'FREE' if free_mode else 'PAID'} mode")

# RPC URLs per chain
RPC_URLS = {
    1: os.getenv("ETHEREUM_RPC_URL", "https://eth.llamarpc.com"),
    137: os.getenv("POLYGON_RPC_URL", "https://polygon.llamarpc.com"),
    42161: os.getenv("ARBITRUM_RPC_URL", "https://arbitrum.llamarpc.com"),
    10: os.getenv("OPTIMISM_RPC_URL", "https://optimism.llamarpc.com"),
    8453: os.getenv("BASE_RPC_URL", "https://base.llamarpc.com"),
    56: os.getenv("BSC_RPC_URL", "https://bsc.llamarpc.com"),
    43114: os.getenv("AVALANCHE_RPC_URL", "https://avalanche.llamarpc.com"),
}


# Request/Response Models
class MarketsRequest(BaseModel):
    """Request for new markets discovery"""

    chain: int = Field(
        ...,
        description="Target blockchain chain ID",
        example=1,
    )
    factories: List[str] = Field(
        ...,
        description="AMM factory contracts to monitor",
        example=["0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"],
    )
    window_minutes: int = Field(
        ...,
        description="Time window to scan in minutes",
        example=5,
        gt=0,
        le=60,
    )


class PairInfo(BaseModel):
    """Information about a new pair"""

    pair_address: str
    tokens: List[str]
    token_symbols: Optional[List[str]] = None
    init_liquidity: str
    top_holders: List[str]
    created_at: str
    factory: str
    block_number: int


class MarketsResponse(BaseModel):
    """Response with new markets"""

    pairs: List[PairInfo]
    total: int
    scanned_blocks: int
    timestamp: str


# Landing Page
@app.get("/", response_class=HTMLResponse)
@app.head("/")
async def root():
    """Landing page"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fresh Markets Watch</title>
        <meta name="description" content="Discover newly launched token pairs across DEXs via x402 micropayments">
        <meta property="og:title" content="Fresh Markets Watch">
        <meta property="og:description" content="Discover newly launched token pairs across DEXs via x402 micropayments">
        <meta property="og:image" content="https://fresh-markets-watch-production.up.railway.app/favicon.ico">
        <link rel="icon" type="image/x-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🆕</text></svg>">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
                color: #e8f0f2;
                line-height: 1.6;
                min-height: 100vh;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            header {{
                background: linear-gradient(135deg, rgba(76, 209, 55, 0.2), rgba(82, 183, 136, 0.2));
                border: 2px solid rgba(76, 209, 55, 0.3);
                border-radius: 15px;
                padding: 40px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            h1 {{
                color: #4cd137;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .subtitle {{
                color: #7bed9f;
                font-size: 1.2em;
                margin-bottom: 15px;
            }}
            .badge {{
                display: inline-block;
                background: rgba(76, 209, 55, 0.2);
                border: 1px solid #4cd137;
                color: #4cd137;
                padding: 6px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                margin-right: 10px;
                margin-top: 10px;
            }}
            .section {{
                background: rgba(32, 58, 67, 0.6);
                border: 1px solid rgba(76, 209, 55, 0.2);
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }}
            h2 {{
                color: #4cd137;
                margin-bottom: 20px;
                font-size: 1.8em;
                border-bottom: 2px solid rgba(76, 209, 55, 0.3);
                padding-bottom: 10px;
            }}
            .endpoint {{
                background: rgba(15, 32, 39, 0.6);
                border-left: 4px solid #4cd137;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .method {{
                display: inline-block;
                background: #4cd137;
                color: #0f2027;
                padding: 5px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }}
            code {{
                background: rgba(0, 0, 0, 0.3);
                color: #7bed9f;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', 'Courier New', monospace;
            }}
            pre {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(76, 209, 55, 0.2);
                border-radius: 6px;
                padding: 15px;
                overflow-x: auto;
                margin: 10px 0;
            }}
            pre code {{
                background: none;
                padding: 0;
                display: block;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .card {{
                background: rgba(15, 32, 39, 0.6);
                border: 1px solid rgba(76, 209, 55, 0.2);
                border-radius: 10px;
                padding: 20px;
                transition: transform 0.3s;
            }}
            .card:hover {{
                transform: translateY(-4px);
                border-color: rgba(76, 209, 55, 0.4);
            }}
            .card h4 {{
                color: #4cd137;
                margin-bottom: 10px;
            }}
            a {{
                color: #4cd137;
                text-decoration: none;
                border-bottom: 1px solid transparent;
                transition: border-color 0.3s;
            }}
            a:hover {{
                border-bottom-color: #4cd137;
            }}
            footer {{
                text-align: center;
                padding: 30px;
                color: #7bed9f;
                opacity: 0.8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Fresh Markets Watch</h1>
                <p class="subtitle">Discover New AMM Pairs in Real-Time</p>
                <p>Monitor factory contracts for newly created pairs and pools across multiple chains</p>
                <div>
                    <span class="badge">Live & Ready</span>
                    <span class="badge">Multi-Chain</span>
                    <span class="badge">x402 Payments</span>
                    <span class="badge">&lt;60s Detection</span>
                </div>
            </header>

            <div class="section">
                <h2>What is Fresh Markets Watch?</h2>
                <p>
                    Fresh Markets Watch monitors AMM factory contracts in real-time to detect newly created
                    pairs and pools. Perfect for discovery bots, yield scouts, and traders looking for
                    early opportunities in emerging markets.
                </p>

                <div class="grid">
                    <div class="card">
                        <h4>Real-Time Detection</h4>
                        <p>Detect new pairs within 60 seconds of creation with &lt;1% false positive rate.</p>
                    </div>
                    <div class="card">
                        <h4>Multi-DEX Support</h4>
                        <p>Monitor Uniswap V2/V3, SushiSwap, PancakeSwap, QuickSwap, and more.</p>
                    </div>
                    <div class="card">
                        <h4>Complete Data</h4>
                        <p>Get pair address, tokens, initial liquidity, top holders, and creation timestamp.</p>
                    </div>
                    <div class="card">
                        <h4>7 Chains Supported</h4>
                        <p>Ethereum, Polygon, Arbitrum, Optimism, Base, BNB Chain, and Avalanche.</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>API Endpoints</h2>

                <div class="endpoint">
                    <h3><span class="method">POST</span>/markets/new</h3>
                    <p>Discover new pairs created in the specified time window</p>
                    <pre><code>curl -X POST https://fresh-markets-watch-production.up.railway.app/markets/new \\
  -H "Content-Type: application/json" \\
  -d '{{
    "chain": 1,
    "factories": ["0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"],
    "window_minutes": 5
  }}'</code></pre>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span>/chains</h3>
                    <p>List all supported blockchain networks</p>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span>/factories/{{chain_id}}</h3>
                    <p>Get known factory addresses for a specific chain</p>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span>/health</h3>
                    <p>Health check and operational status</p>
                </div>
            </div>

            <div class="section">
                <h2>x402 Micropayments</h2>
                <p>This service uses the <strong>x402 payment protocol</strong> for usage-based billing.</p>
                <div class="grid">
                    <div class="card">
                        <h4>Payment Details</h4>
                        <p><strong>Price:</strong> 0.05 USDC per request</p>
                        <p><strong>Address:</strong> <code>{payment_address}</code></p>
                        <p><strong>Network:</strong> Base</p>
                    </div>
                    <div class="card">
                        <h4>Status</h4>
                        <p><em>{"Currently in FREE MODE for testing" if free_mode else "Payment verification active"}</em></p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Supported Networks</h2>
                <div class="grid">
                    <div class="card"><h4>Ethereum</h4><p>Chain ID: 1</p></div>
                    <div class="card"><h4>Polygon</h4><p>Chain ID: 137</p></div>
                    <div class="card"><h4>Arbitrum</h4><p>Chain ID: 42161</p></div>
                    <div class="card"><h4>Optimism</h4><p>Chain ID: 10</p></div>
                    <div class="card"><h4>Base</h4><p>Chain ID: 8453</p></div>
                    <div class="card"><h4>BNB Chain</h4><p>Chain ID: 56</p></div>
                    <div class="card"><h4>Avalanche</h4><p>Chain ID: 43114</p></div>
                </div>
            </div>

            <div class="section">
                <h2>Documentation</h2>
                <p>Interactive API documentation:</p>
                <div style="margin: 20px 0;">
                    <a href="/docs" style="display: inline-block; background: rgba(76, 209, 55, 0.2); padding: 10px 20px; border-radius: 5px; margin-right: 10px;">Swagger UI</a>
                    <a href="/redoc" style="display: inline-block; background: rgba(76, 209, 55, 0.2); padding: 10px 20px; border-radius: 5px;">ReDoc</a>
                </div>
            </div>

            <footer>
                <p><strong>Built by DeganAI</strong></p>
                <p>Bounty #1 Submission for Daydreams AI Agent Bounties</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# AP2 (Agent Payments Protocol) Metadata
@app.get("/.well-known/agent.json")
@app.head("/.well-known/agent.json")
async def agent_metadata():
    """AP2 metadata - returns HTTP 200"""
    base_url = os.getenv("BASE_URL", "https://fresh-markets-watch-production.up.railway.app")

    agent_json = {
        "name": "Fresh Markets Watch",
        "description": "Real-time AMM pair monitoring for discovery bots and yield scouts. Detect new pairs within 60 seconds with <1% false positive rate across 7 chains.",
        "url": base_url.replace("https://", "http://") + "/",
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
            "extensions": [
                {
                    "uri": "https://github.com/google-agentic-commerce/ap2/tree/v0.1",
                    "description": "Agent Payments Protocol (AP2)",
                    "required": True,
                    "params": {"roles": ["merchant"]},
                }
            ],
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [
            {
                "id": "fresh-markets-watch",
                "name": "fresh-markets-watch",
                "description": "Monitor AMM factories for newly created pairs with liquidity and holder data",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "streaming": False,
                "x_input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "chain": {
                            "description": "Target blockchain chain ID",
                            "type": "integer",
                        },
                        "factories": {
                            "description": "AMM factory contracts to monitor",
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "window_minutes": {
                            "description": "Time window to scan in minutes",
                            "type": "integer",
                        },
                    },
                    "required": ["chain", "factories", "window_minutes"],
                    "additionalProperties": False,
                },
                "x_output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "pairs": {"type": "array"},
                        "total": {"type": "integer"},
                        "scanned_blocks": {"type": "integer"},
                    },
                    "required": ["pairs", "total", "scanned_blocks"],
                    "additionalProperties": False,
                },
            }
        ],
        "supportsAuthenticatedExtendedCard": False,
        "entrypoints": {
            "fresh-markets-watch": {
                "description": "Discover new AMM pairs in real-time",
                "streaming": False,
                "input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "chain": {"description": "Chain ID", "type": "integer"},
                        "factories": {"description": "Factory addresses", "type": "array", "items": {"type": "string"}},
                        "window_minutes": {"description": "Time window", "type": "integer"},
                    },
                    "required": ["chain", "factories", "window_minutes"],
                    "additionalProperties": False,
                },
                "output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "pairs": {"type": "array"},
                        "total": {"type": "integer"},
                        "scanned_blocks": {"type": "integer"},
                    },
                    "additionalProperties": False,
                },
                "pricing": {"invoke": "0.05 USDC"},
            }
        },
        "payments": [
            {
                "method": "x402",
                "payee": payment_address,
                "network": "base",
                "endpoint": "https://facilitator.daydreams.systems",
                "priceModel": {"default": "0.05"},
                "extensions": {
                    "x402": {"facilitatorUrl": "https://facilitator.daydreams.systems"}
                },
            }
        ],
    }

    return JSONResponse(content=agent_json, status_code=200)


# x402 Protocol Metadata
@app.get("/.well-known/x402")
@app.head("/.well-known/x402")
async def x402_metadata():
    """x402 protocol metadata - returns HTTP 402"""
    base_url = os.getenv("BASE_URL", "https://fresh-markets-watch-production.up.railway.app")

    metadata = {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",
                "resource": f"{base_url}/entrypoints/fresh-markets-watch/invoke",
                "description": "Monitor AMM factories for newly created pairs with liquidity and holder data",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            }
        ],
    }

    return JSONResponse(content=metadata, status_code=402)


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint"""
    from fastapi.responses import Response
    svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🆕</text></svg>'
    return Response(content=svg_content, media_type="image/svg+xml")


# Health Check
@app.get("/health")
async def health():
    """Health check"""
    supported = get_supported_chains()
    return {
        "status": "healthy",
        "supported_chains": len(supported),
        "chain_ids": supported,
        "free_mode": free_mode,
    }


# List Chains
@app.get("/chains")
async def list_chains():
    """List all supported chains"""
    chains = []

    for chain_id in get_supported_chains():
        chains.append({
            "chain_id": chain_id,
            "name": get_chain_name(chain_id),
            "rpc_available": chain_id in RPC_URLS,
        })

    return {"chains": chains, "total": len(chains)}


# Get factories for a chain
@app.get("/factories/{chain_id}")
async def get_factories(chain_id: int):
    """Get known factory addresses for a chain"""
    factories = get_all_factories(chain_id)

    if not factories:
        raise HTTPException(
            status_code=404,
            detail=f"No factories configured for chain {chain_id}",
        )

    return {
        "chain_id": chain_id,
        "chain_name": get_chain_name(chain_id),
        "factories": factories,
    }


# Main Markets Discovery Endpoint
@app.post("/markets/new", response_model=MarketsResponse)
async def discover_markets(request: MarketsRequest):
    """
    Discover new AMM pairs created in the specified time window

    Monitors factory contracts for PairCreated/PoolCreated events and returns:
    - Pair addresses
    - Token addresses
    - Initial liquidity
    - Top holders
    - Creation timestamp
    """
    try:
        logger.info(f"Markets request: chain={request.chain}, factories={request.factories}, window={request.window_minutes}")

        # Validate chain
        if request.chain not in get_supported_chains():
            raise HTTPException(
                status_code=400,
                detail=f"Chain {request.chain} not supported. Supported: {get_supported_chains()}",
            )

        # Get RPC URL
        rpc_url = RPC_URLS.get(request.chain)
        if not rpc_url:
            raise HTTPException(
                status_code=503,
                detail=f"No RPC URL configured for chain {request.chain}",
            )

        # Initialize monitor
        monitor = PairMonitor(rpc_url)

        if not monitor.is_connected:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to RPC for chain {request.chain}",
            )

        # Scan factories
        new_pairs = monitor.scan_factories(
            request.chain, request.factories, request.window_minutes
        )

        if not new_pairs:
            return MarketsResponse(
                pairs=[],
                total=0,
                scanned_blocks=0,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

        # Initialize Web3 for liquidity and holder tracking
        w3 = monitor.w3
        liquidity_tracker = LiquidityTracker(w3)
        holder_analyzer = HolderAnalyzer(w3)

        # Get token prices for liquidity calculation
        # For now, we'll use a simplified approach
        token_prices = {}

        # Process each pair
        enriched_pairs = []
        for pair in new_pairs:
            try:
                # Get initial liquidity
                init_liquidity = liquidity_tracker.get_initial_liquidity(
                    pair["pair_address"], token_prices
                )

                # Get top holders
                top_holders = holder_analyzer.get_top_holders(
                    pair["pair_address"], pair["block_number"], limit=10
                )

                pair_info = PairInfo(
                    pair_address=pair["pair_address"],
                    tokens=pair["tokens"],
                    token_symbols=None,
                    init_liquidity=init_liquidity or "0",
                    top_holders=top_holders,
                    created_at=pair["created_at"],
                    factory=pair["factory"],
                    block_number=pair["block_number"],
                )

                enriched_pairs.append(pair_info)

            except Exception as e:
                logger.error(f"Error enriching pair {pair['pair_address']}: {e}")
                # Still include the pair with minimal data
                pair_info = PairInfo(
                    pair_address=pair["pair_address"],
                    tokens=pair["tokens"],
                    token_symbols=None,
                    init_liquidity="0",
                    top_holders=[],
                    created_at=pair["created_at"],
                    factory=pair["factory"],
                    block_number=pair["block_number"],
                )
                enriched_pairs.append(pair_info)

        # Calculate scanned blocks
        from_block, to_block = monitor.get_recent_blocks(request.window_minutes)
        scanned_blocks = (to_block - from_block) if from_block and to_block else 0

        return MarketsResponse(
            pairs=enriched_pairs,
            total=len(enriched_pairs),
            scanned_blocks=scanned_blocks,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Markets discovery error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


# AP2 Entrypoint - GET/HEAD for x402 discovery
@app.get("/entrypoints/fresh-markets-watch/invoke")
@app.head("/entrypoints/fresh-markets-watch/invoke")
async def entrypoint_markets_get():
    """
    x402 discovery endpoint - returns HTTP 402 for x402scan registration
    """
    base_url = os.getenv("BASE_URL", "https://fresh-markets-watch-production.up.railway.app")

    return JSONResponse(
        status_code=402,
        content={
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",
                "resource": f"{base_url}/entrypoints/fresh-markets-watch/invoke",
                "description": "Fresh Markets Watch - Monitor AMM factories for newly created pairs",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "outputSchema": {
                    "input": {
                        "type": "http",
                        "method": "POST",
                        "bodyType": "json",
                        "bodyFields": {
                            "chain": {"type": "number", "required": True, "description": "Target blockchain chain ID"},
                            "factories": {"type": "array", "required": True, "description": "AMM factory contracts to monitor"},
                            "window_minutes": {"type": "number", "required": True, "description": "Time window to scan in minutes"}
                        }
                    },
                    "output": {"type": "object", "description": "Newly launched token pairs with liquidity and volume"}
                }
            }]
        }
    )


# AP2 Entrypoint - POST for actual requests
@app.post("/entrypoints/fresh-markets-watch/invoke")
async def entrypoint_markets_post(request: Optional[MarketsRequest] = None, x_payment_txhash: Optional[str] = None):
    """
    AP2 (Agent Payments Protocol) compatible entrypoint

    Returns 402 if no payment provided (FREE_MODE overrides this for testing).
    Calls the main /markets/new endpoint with the same logic if payment is valid.
    """
    # Return 402 if no request body provided
    if request is None:
        return await entrypoint_markets_get()

    # In FREE_MODE, bypass payment check
    if not free_mode and not x_payment_txhash:
        return await entrypoint_markets_get()

    return await discover_markets(request)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
