"""
Track initial liquidity for new pairs
"""
import logging
from typing import Optional, Dict
from web3 import Web3

logger = logging.getLogger(__name__)

# Uniswap V2 Pair ABI (getReserves function)
PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"},
        ],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
]

# ERC20 ABI for token info
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]


class LiquidityTracker:
    """Track liquidity for pairs"""

    def __init__(self, w3: Web3):
        """
        Initialize liquidity tracker

        Args:
            w3: Web3 instance
        """
        self.w3 = w3

    def get_pair_reserves(self, pair_address: str) -> Optional[Dict]:
        """
        Get reserves from pair contract

        Args:
            pair_address: Pair contract address

        Returns:
            Dict with reserve0, reserve1, or None
        """
        try:
            pair_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(pair_address), abi=PAIR_ABI
            )

            reserves = pair_contract.functions.getReserves().call()

            return {
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "timestamp": reserves[2],
            }

        except Exception as e:
            logger.error(f"Error getting reserves for {pair_address}: {e}")
            return None

    def get_token_info(self, token_address: str) -> Optional[Dict]:
        """
        Get token symbol and decimals

        Args:
            token_address: Token contract address

        Returns:
            Dict with symbol and decimals, or None
        """
        try:
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
            )

            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()

            return {"symbol": symbol, "decimals": decimals}

        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {e}")
            return None

    def calculate_liquidity_usd(
        self, reserve0: int, reserve1: int, token0_price: float, token1_price: float
    ) -> float:
        """
        Calculate total liquidity in USD

        Args:
            reserve0: Reserve of token0
            reserve1: Reserve of token1
            token0_price: Price of token0 in USD
            token1_price: Price of token1 in USD

        Returns:
            Total liquidity in USD
        """
        try:
            # Convert to human readable (assuming 18 decimals)
            reserve0_human = reserve0 / 10**18
            reserve1_human = reserve1 / 10**18

            # Calculate USD value
            liquidity_usd = (reserve0_human * token0_price) + (
                reserve1_human * token1_price
            )

            return liquidity_usd

        except Exception as e:
            logger.error(f"Error calculating liquidity: {e}")
            return 0.0

    def get_initial_liquidity(
        self, pair_address: str, token_prices: Dict[str, float]
    ) -> Optional[str]:
        """
        Get initial liquidity for a pair

        Args:
            pair_address: Pair address
            token_prices: Dict of token symbols to USD prices

        Returns:
            Liquidity in USD as string, or "0"
        """
        try:
            reserves = self.get_pair_reserves(pair_address)
            if not reserves:
                return "0"

            # Get token addresses
            pair_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(pair_address), abi=PAIR_ABI
            )

            token0_addr = pair_contract.functions.token0().call()
            token1_addr = pair_contract.functions.token1().call()

            # Get token info
            token0_info = self.get_token_info(token0_addr)
            token1_info = self.get_token_info(token1_addr)

            if not token0_info or not token1_info:
                return "0"

            # Get prices (default to 0 if not found)
            token0_price = token_prices.get(token0_info["symbol"], 0.0)
            token1_price = token_prices.get(token1_info["symbol"], 0.0)

            # Calculate liquidity
            liquidity_usd = self.calculate_liquidity_usd(
                reserves["reserve0"],
                reserves["reserve1"],
                token0_price,
                token1_price,
            )

            return f"{liquidity_usd:.2f}"

        except Exception as e:
            logger.error(f"Error getting initial liquidity: {e}")
            return "0"
