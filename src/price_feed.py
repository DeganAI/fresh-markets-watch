"""
Token price fetching from CoinGecko API
"""
import httpx
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"

# Token symbol to CoinGecko ID mapping
TOKEN_ID_MAP = {
    "ETH": "ethereum",
    "WETH": "ethereum",
    "MATIC": "matic-network",
    "POL": "matic-network",
    "BNB": "binancecoin",
    "AVAX": "avalanche-2",
    "ARB": "arbitrum",
    "OP": "optimism",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "WBTC": "wrapped-bitcoin",
}


async def get_token_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch token prices from CoinGecko

    Args:
        symbols: List of token symbols (e.g., ['ETH', 'USDC'])

    Returns:
        Dictionary mapping symbols to USD prices
    """
    try:
        # Convert symbols to CoinGecko IDs
        ids = []
        symbol_to_id = {}

        for symbol in symbols:
            symbol_upper = symbol.upper()
            gecko_id = TOKEN_ID_MAP.get(symbol_upper)

            if gecko_id:
                ids.append(gecko_id)
                symbol_to_id[gecko_id] = symbol_upper
            else:
                logger.warning(f"No CoinGecko ID mapping for {symbol}")

        if not ids:
            logger.error("No valid token IDs to fetch")
            return {}

        # Fetch prices
        ids_str = ",".join(ids)
        url = f"{COINGECKO_API}/simple/price"
        params = {
            "ids": ids_str,
            "vs_currencies": "usd"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        # Map back to symbols
        prices = {}
        for gecko_id, price_data in data.items():
            symbol = symbol_to_id.get(gecko_id)
            if symbol and "usd" in price_data:
                prices[symbol] = price_data["usd"]

        logger.info(f"Fetched prices for {len(prices)} tokens")
        return prices

    except Exception as e:
        logger.error(f"Error fetching token prices: {e}")
        return {}


async def get_token_price(symbol: str) -> float:
    """
    Fetch single token price

    Args:
        symbol: Token symbol (e.g., 'ETH')

    Returns:
        Price in USD or 0.0 if not found
    """
    prices = await get_token_prices([symbol])
    return prices.get(symbol.upper(), 0.0)
