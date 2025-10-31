"""
x402 Payment Verification Middleware

Verifies USDC payments on Ethereum before serving requests
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from web3 import Web3
import logging
import os
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class X402Middleware:
    """HTTP 402 Payment Required middleware"""

    # USDC contract on Ethereum
    USDC_CONTRACT = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    # Minimum payment amount (in USDC, 6 decimals)
    MIN_PAYMENT_USDC = 0.05  # $0.05 per request

    def __init__(
        self,
        payment_address: str,
        ethereum_rpc_url: str,
        free_mode: bool = False,
    ):
        """
        Initialize x402 middleware

        Args:
            payment_address: Ethereum address to receive payments
            ethereum_rpc_url: Ethereum RPC endpoint
            free_mode: If True, skip payment verification (for testing)
        """
        self.payment_address = payment_address
        self.free_mode = free_mode

        if not free_mode:
            # Initialize Web3
            self.w3 = Web3(Web3.HTTPProvider(ethereum_rpc_url))

            if not self.w3.is_connected():
                logger.error("Failed to connect to Ethereum RPC")
                raise ConnectionError("Cannot connect to Ethereum")

            # USDC contract ABI (minimal - just balanceOf and Transfer event)
            usdc_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "from", "type": "address"},
                        {"indexed": True, "name": "to", "type": "address"},
                        {"indexed": False, "name": "value", "type": "uint256"},
                    ],
                    "name": "Transfer",
                    "type": "event",
                },
            ]

            self.usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.USDC_CONTRACT),
                abi=usdc_abi,
            )

            logger.info(f"x402 middleware initialized (payment address: {payment_address})")
        else:
            logger.warning("x402 middleware in FREE MODE - no payment verification")

    async def verify_payment(self, request: Request) -> bool:
        """
        Verify payment from request headers

        Expects header: X-Payment-TxHash with transaction hash

        Args:
            request: FastAPI request

        Returns:
            True if payment is valid

        Raises:
            HTTPException if payment is invalid
        """
        if self.free_mode:
            logger.debug("Free mode - skipping payment verification")
            return True

        # Get payment tx hash from header
        tx_hash = request.headers.get("X-Payment-TxHash")

        if not tx_hash:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Payment Required",
                    "message": "Send USDC payment and include X-Payment-TxHash header",
                    "payment_address": self.payment_address,
                    "usdc_contract": self.USDC_CONTRACT,
                    "min_amount_usdc": self.MIN_PAYMENT_USDC,
                    "instructions": "Send USDC to payment address, then include transaction hash in X-Payment-TxHash header",
                },
            )

        try:
            # Get transaction receipt
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)

            if not tx_receipt or tx_receipt.get("status") != 1:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Transaction failed or not found",
                )

            # Verify transaction is recent (within last hour)
            block = self.w3.eth.get_block(tx_receipt["blockNumber"])
            tx_time = datetime.fromtimestamp(block["timestamp"])
            if datetime.now() - tx_time > timedelta(hours=1):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Payment transaction too old (must be within 1 hour)",
                )

            # Parse logs for USDC Transfer event
            transfer_found = False
            payment_amount = 0

            for log in tx_receipt["logs"]:
                # Check if it's from USDC contract
                if log["address"].lower() != self.USDC_CONTRACT.lower():
                    continue

                try:
                    # Decode Transfer event
                    event = self.usdc_contract.events.Transfer().process_log(log)

                    # Check if payment is to our address
                    if event["args"]["to"].lower() == self.payment_address.lower():
                        transfer_found = True
                        payment_amount = event["args"]["value"] / 1e6  # USDC has 6 decimals

                        logger.info(f"Payment verified: {payment_amount} USDC from {tx_hash}")
                        break

                except Exception as e:
                    logger.debug(f"Failed to decode log: {e}")
                    continue

            if not transfer_found:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"No USDC payment found to {self.payment_address}",
                )

            # Verify amount is sufficient
            if payment_amount < self.MIN_PAYMENT_USDC:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Payment too small: {payment_amount} USDC (minimum: {self.MIN_PAYMENT_USDC} USDC)",
                )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment verification failed: {str(e)}",
            )

    async def __call__(self, request: Request, call_next):
        """
        Middleware entry point

        Args:
            request: FastAPI request
            call_next: Next middleware/route

        Returns:
            Response from route handler
        """
        # Skip payment check for health/info endpoints
        if request.url.path in ["/health", "/", "/info"]:
            return await call_next(request)

        # Verify payment
        try:
            await self.verify_payment(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail,
            )

        # Process request
        response = await call_next(request)
        return response
