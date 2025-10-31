"""
Monitor factory contracts for new pair creation events
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from web3 import Web3
from web3.exceptions import Web3Exception

from src.factory_config import (
    PAIR_CREATED_EVENT_SIGNATURE,
    POOL_CREATED_EVENT_SIGNATURE,
    get_all_factories,
)

logger = logging.getLogger(__name__)


# Uniswap V2 PairCreated event ABI
PAIR_CREATED_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "token0", "type": "address"},
        {"indexed": True, "name": "token1", "type": "address"},
        {"indexed": False, "name": "pair", "type": "address"},
        {"indexed": False, "name": "", "type": "uint256"},
    ],
    "name": "PairCreated",
    "type": "event",
}

# Uniswap V3 PoolCreated event ABI
POOL_CREATED_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "token0", "type": "address"},
        {"indexed": True, "name": "token1", "type": "address"},
        {"indexed": True, "name": "fee", "type": "uint24"},
        {"indexed": False, "name": "tickSpacing", "type": "int24"},
        {"indexed": False, "name": "pool", "type": "address"},
    ],
    "name": "PoolCreated",
    "type": "event",
}


class PairMonitor:
    """Monitor AMM factories for new pair creation"""

    def __init__(self, rpc_url: str):
        """
        Initialize pair monitor

        Args:
            rpc_url: Web3 RPC endpoint
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.is_connected = self.w3.is_connected()

        if not self.is_connected:
            logger.warning(f"Failed to connect to RPC: {rpc_url}")

    def get_recent_blocks(self, window_minutes: int) -> tuple:
        """
        Calculate block range for time window

        Args:
            window_minutes: Time window in minutes

        Returns:
            Tuple of (from_block, to_block)
        """
        try:
            current_block = self.w3.eth.block_number

            # Estimate blocks per minute (varies by chain)
            # Ethereum: ~5 blocks/min, Polygon: ~30 blocks/min, etc.
            # Use conservative estimate of 12 blocks/min as average
            blocks_back = window_minutes * 12

            from_block = max(0, current_block - blocks_back)

            logger.info(f"Scanning blocks {from_block} to {current_block}")
            return from_block, current_block

        except Exception as e:
            logger.error(f"Error calculating block range: {e}")
            return None, None

    def get_pair_created_events(
        self, factory_address: str, from_block: int, to_block: int, is_v3: bool = False
    ) -> List[Dict]:
        """
        Fetch PairCreated events from factory

        Args:
            factory_address: Factory contract address
            from_block: Start block
            to_block: End block
            is_v3: Whether this is Uniswap V3 (uses PoolCreated event)

        Returns:
            List of event data
        """
        try:
            # Create event signature
            event_signature = POOL_CREATED_EVENT_SIGNATURE if is_v3 else PAIR_CREATED_EVENT_SIGNATURE

            # Get logs
            logs = self.w3.eth.get_logs({
                "address": Web3.to_checksum_address(factory_address),
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [event_signature],
            })

            events = []
            for log in logs:
                try:
                    # Decode event
                    if is_v3:
                        # V3 PoolCreated: token0, token1, fee (indexed), tickSpacing, pool
                        event_data = {
                            "token0": "0x" + log["topics"][1].hex()[-40:],
                            "token1": "0x" + log["topics"][2].hex()[-40:],
                            "pair_address": "0x" + log["data"].hex()[-40:],
                            "block_number": log["blockNumber"],
                            "transaction_hash": log["transactionHash"].hex(),
                            "factory": factory_address,
                        }
                    else:
                        # V2 PairCreated: token0, token1 (indexed), pair, allPairsLength
                        event_data = {
                            "token0": "0x" + log["topics"][1].hex()[-40:],
                            "token1": "0x" + log["topics"][2].hex()[-40:],
                            "pair_address": "0x" + log["data"].hex()[26:66],
                            "block_number": log["blockNumber"],
                            "transaction_hash": log["transactionHash"].hex(),
                            "factory": factory_address,
                        }

                    events.append(event_data)

                except Exception as e:
                    logger.error(f"Error decoding event: {e}")
                    continue

            logger.info(f"Found {len(events)} pair creation events from {factory_address}")
            return events

        except Exception as e:
            logger.error(f"Error fetching events from {factory_address}: {e}")
            return []

    def get_block_timestamp(self, block_number: int) -> Optional[datetime]:
        """
        Get timestamp for a block

        Args:
            block_number: Block number

        Returns:
            Datetime of block or None
        """
        try:
            block = self.w3.eth.get_block(block_number)
            return datetime.utcfromtimestamp(block["timestamp"])
        except Exception as e:
            logger.error(f"Error getting block timestamp: {e}")
            return None

    def scan_factories(
        self, chain_id: int, factories: List[str], window_minutes: int
    ) -> List[Dict]:
        """
        Scan multiple factories for new pairs

        Args:
            chain_id: Chain ID
            factories: List of factory addresses to scan
            window_minutes: Time window in minutes

        Returns:
            List of new pairs found
        """
        if not self.is_connected:
            logger.error("Web3 not connected")
            return []

        # Get block range
        from_block, to_block = self.get_recent_blocks(window_minutes)
        if from_block is None:
            return []

        all_pairs = []
        factory_map = get_all_factories(chain_id)

        for factory_addr in factories:
            # Determine if this is V3 (check if address matches known V3 factories)
            is_v3 = False
            for name, addr in factory_map.items():
                if addr.lower() == factory_addr.lower() and "v3" in name.lower():
                    is_v3 = True
                    break

            # Get events
            events = self.get_pair_created_events(
                factory_addr, from_block, to_block, is_v3=is_v3
            )

            for event in events:
                # Get block timestamp
                created_at = self.get_block_timestamp(event["block_number"])

                pair_info = {
                    "pair_address": event["pair_address"],
                    "tokens": [event["token0"], event["token1"]],
                    "factory": event["factory"],
                    "created_at": created_at.isoformat() + "Z" if created_at else None,
                    "block_number": event["block_number"],
                    "transaction_hash": event["transaction_hash"],
                }

                all_pairs.append(pair_info)

        # Remove duplicates
        seen = set()
        unique_pairs = []
        for pair in all_pairs:
            pair_key = pair["pair_address"].lower()
            if pair_key not in seen:
                seen.add(pair_key)
                unique_pairs.append(pair)

        logger.info(f"Found {len(unique_pairs)} unique new pairs")
        return unique_pairs
