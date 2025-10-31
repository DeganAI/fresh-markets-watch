"""
Analyze top holders of a pair
"""
import logging
from typing import List, Dict
from web3 import Web3

logger = logging.getLogger(__name__)

# Transfer event signature
TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Dead addresses to exclude
DEAD_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}


class HolderAnalyzer:
    """Analyze token holders for pairs"""

    def __init__(self, w3: Web3):
        """
        Initialize holder analyzer

        Args:
            w3: Web3 instance
        """
        self.w3 = w3

    def get_transfer_events(
        self, pair_address: str, from_block: int, to_block: int
    ) -> List[Dict]:
        """
        Get Transfer events from pair contract

        Args:
            pair_address: Pair contract address
            from_block: Start block
            to_block: End block

        Returns:
            List of transfer events
        """
        try:
            logs = self.w3.eth.get_logs({
                "address": Web3.to_checksum_address(pair_address),
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [TRANSFER_EVENT_SIGNATURE],
            })

            transfers = []
            for log in logs:
                try:
                    # Decode Transfer event
                    from_addr = "0x" + log["topics"][1].hex()[-40:]
                    to_addr = "0x" + log["topics"][2].hex()[-40:]
                    value = int(log["data"].hex(), 16)

                    transfers.append({
                        "from": from_addr,
                        "to": to_addr,
                        "value": value,
                    })

                except Exception as e:
                    logger.error(f"Error decoding transfer: {e}")
                    continue

            logger.info(f"Found {len(transfers)} transfers for {pair_address}")
            return transfers

        except Exception as e:
            logger.error(f"Error getting transfer events: {e}")
            return []

    def calculate_holder_balances(self, transfers: List[Dict]) -> Dict[str, int]:
        """
        Calculate holder balances from transfers

        Args:
            transfers: List of transfer events

        Returns:
            Dict mapping addresses to balances
        """
        balances = {}

        for transfer in transfers:
            from_addr = transfer["from"].lower()
            to_addr = transfer["to"].lower()
            value = transfer["value"]

            # Subtract from sender
            if from_addr not in DEAD_ADDRESSES:
                balances[from_addr] = balances.get(from_addr, 0) - value

            # Add to recipient
            if to_addr not in DEAD_ADDRESSES:
                balances[to_addr] = balances.get(to_addr, 0) + value

        # Filter out zero/negative balances and dead addresses
        balances = {
            addr: bal
            for addr, bal in balances.items()
            if bal > 0 and addr.lower() not in DEAD_ADDRESSES
        }

        return balances

    def get_top_holders(
        self, pair_address: str, creation_block: int, limit: int = 10
    ) -> List[str]:
        """
        Get top holders of a pair

        Args:
            pair_address: Pair address
            creation_block: Block when pair was created
            limit: Number of top holders to return

        Returns:
            List of holder addresses
        """
        try:
            # Get current block
            current_block = self.w3.eth.block_number

            # Get transfer events
            transfers = self.get_transfer_events(
                pair_address, creation_block, current_block
            )

            if not transfers:
                logger.warning(f"No transfers found for {pair_address}")
                return []

            # Calculate balances
            balances = self.calculate_holder_balances(transfers)

            # Sort by balance and get top N
            sorted_holders = sorted(
                balances.items(), key=lambda x: x[1], reverse=True
            )

            top_holders = [addr for addr, bal in sorted_holders[:limit]]

            logger.info(f"Found {len(top_holders)} top holders for {pair_address}")
            return top_holders

        except Exception as e:
            logger.error(f"Error getting top holders: {e}")
            return []
