"""
Pair Analyzer

Analyzes new AMM pairs to get initial liquidity and top token holders
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from web3 import Web3
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class PairAnalyzer:
    """Analyze AMM pairs for liquidity and holder information"""

    # ERC20 ABI for common functions
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function",
        },
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
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function",
        },
    ]

    # Uniswap V2 Pair ABI
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

    # Etherscan API endpoints
    EXPLORER_APIS = {
        "ethereum": "https://api.etherscan.io/api",
        "base": "https://api.basescan.org/api",
        "arbitrum": "https://api.arbiscan.io/api",
    }

    def __init__(
        self,
        rpc_url: str,
        chain: str = "ethereum",
        explorer_api_key: Optional[str] = None,
    ):
        """
        Initialize pair analyzer

        Args:
            rpc_url: RPC endpoint URL
            chain: Chain name (ethereum, base, arbitrum)
            explorer_api_key: Block explorer API key (optional)
        """
        self.chain = chain.lower()
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.explorer_api_key = explorer_api_key

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {chain} RPC")

        logger.info(f"PairAnalyzer initialized for {chain}")

    def get_token_contract(self, token_address: str):
        """Get ERC20 token contract instance"""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=self.ERC20_ABI,
        )

    def get_pair_contract(self, pair_address: str):
        """Get pair contract instance"""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(pair_address),
            abi=self.PAIR_ABI,
        )

    async def get_token_info(self, token_address: str) -> Dict:
        """
        Get token metadata

        Args:
            token_address: Token contract address

        Returns:
            Dict with symbol, name, decimals, total_supply
        """
        try:
            contract = self.get_token_contract(token_address)

            symbol = "UNKNOWN"
            name = "Unknown Token"
            decimals = 18
            total_supply = 0

            try:
                symbol = contract.functions.symbol().call()
            except Exception:
                pass

            try:
                name = contract.functions.name().call()
            except Exception:
                pass

            try:
                decimals = contract.functions.decimals().call()
            except Exception:
                pass

            try:
                total_supply = contract.functions.totalSupply().call()
            except Exception:
                pass

            return {
                "address": token_address,
                "symbol": symbol,
                "name": name,
                "decimals": decimals,
                "total_supply": str(total_supply),
            }

        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {e}")
            return {
                "address": token_address,
                "symbol": "UNKNOWN",
                "name": "Unknown Token",
                "decimals": 18,
                "total_supply": "0",
            }

    async def get_initial_liquidity(
        self,
        pair_address: str,
        token0: str,
        token1: str,
    ) -> Dict:
        """
        Get initial liquidity for a pair

        Args:
            pair_address: Pair contract address
            token0: First token address
            token1: Second token address

        Returns:
            Dict with reserve0, reserve1, and token info
        """
        try:
            pair_contract = self.get_pair_contract(pair_address)

            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            reserve0 = reserves[0]
            reserve1 = reserves[1]

            # Get token info
            token0_info = await self.get_token_info(token0)
            token1_info = await self.get_token_info(token1)

            # Calculate human-readable amounts
            amount0 = reserve0 / (10 ** token0_info["decimals"])
            amount1 = reserve1 / (10 ** token1_info["decimals"])

            return {
                "reserve0": str(reserve0),
                "reserve1": str(reserve1),
                "amount0": amount0,
                "amount1": amount1,
                "token0": token0_info,
                "token1": token1_info,
            }

        except Exception as e:
            logger.error(f"Error getting liquidity for {pair_address}: {e}")
            return {
                "reserve0": "0",
                "reserve1": "0",
                "amount0": 0,
                "amount1": 0,
                "token0": await self.get_token_info(token0),
                "token1": await self.get_token_info(token1),
            }

    async def get_top_holders_via_explorer(
        self,
        token_address: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get top token holders via block explorer API

        Args:
            token_address: Token contract address
            limit: Number of top holders to return

        Returns:
            List of holder dicts with address and balance
        """
        if not self.explorer_api_key:
            logger.warning("No explorer API key - skipping holder analysis")
            return []

        explorer_url = self.EXPLORER_APIS.get(self.chain)
        if not explorer_url:
            logger.warning(f"No explorer API for chain {self.chain}")
            return []

        try:
            params = {
                "module": "token",
                "action": "tokenholderlist",
                "contractaddress": token_address,
                "page": 1,
                "offset": limit,
                "apikey": self.explorer_api_key,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(explorer_url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if data.get("status") == "1" and data.get("result"):
                            holders = []
                            for holder in data["result"][:limit]:
                                holders.append({
                                    "address": holder.get("TokenHolderAddress"),
                                    "balance": holder.get("TokenHolderQuantity"),
                                })
                            return holders

        except Exception as e:
            logger.error(f"Error fetching holders for {token_address}: {e}")

        return []

    async def get_top_holders_onchain(
        self,
        token_address: str,
        known_addresses: List[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get top holders by checking known addresses on-chain

        Args:
            token_address: Token contract address
            known_addresses: List of addresses to check (e.g., known whales)
            limit: Max holders to return

        Returns:
            List of holder dicts with address and balance
        """
        if not known_addresses:
            # Common addresses to check
            known_addresses = [
                "0x0000000000000000000000000000000000000000",  # Zero address (burn)
                "0x000000000000000000000000000000000000dEaD",  # Dead address
            ]

        try:
            contract = self.get_token_contract(token_address)
            holders = []

            for address in known_addresses[:limit]:
                try:
                    balance = contract.functions.balanceOf(
                        Web3.to_checksum_address(address)
                    ).call()

                    if balance > 0:
                        holders.append({
                            "address": address,
                            "balance": str(balance),
                        })
                except Exception:
                    continue

            # Sort by balance descending
            holders.sort(key=lambda x: int(x["balance"]), reverse=True)
            return holders[:limit]

        except Exception as e:
            logger.error(f"Error getting on-chain holders for {token_address}: {e}")
            return []

    async def analyze_pair(self, pair_data: Dict) -> Dict:
        """
        Analyze a pair completely

        Args:
            pair_data: Pair data from monitor

        Returns:
            Complete pair analysis with liquidity and holders
        """
        pair_address = pair_data["pair_address"]
        tokens = pair_data["tokens"]

        logger.info(f"Analyzing pair {pair_address}")

        # Get liquidity info
        liquidity = await self.get_initial_liquidity(
            pair_address,
            tokens[0],
            tokens[1],
        )

        # Get top holders for both tokens
        holders_tasks = [
            self.get_top_holders_via_explorer(tokens[0], limit=5),
            self.get_top_holders_via_explorer(tokens[1], limit=5),
        ]

        holders_results = await asyncio.gather(*holders_tasks, return_exceptions=True)

        token0_holders = holders_results[0] if not isinstance(holders_results[0], Exception) else []
        token1_holders = holders_results[1] if not isinstance(holders_results[1], Exception) else []

        # Build complete analysis
        analysis = {
            **pair_data,
            "init_liquidity": liquidity,
            "top_holders": {
                "token0": token0_holders,
                "token1": token1_holders,
            },
        }

        return analysis
