"""
Factory contract configurations for major AMMs across chains
"""

# AMM Factory addresses per chain
FACTORY_ADDRESSES = {
    # Ethereum Mainnet (1)
    1: {
        "uniswap_v2": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "sushiswap": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
    },
    # Polygon (137)
    137: {
        "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
        "quickswap": "0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32",
    },
    # Arbitrum (42161)
    42161: {
        "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
    },
    # Optimism (10)
    10: {
        "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    },
    # Base (8453)
    8453: {
        "uniswap_v3": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    },
    # BNB Chain (56)
    56: {
        "pancakeswap": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
        "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
    },
    # Avalanche (43114)
    43114: {
        "traderjoe": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10",
        "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
    },
}

# Chain names
CHAIN_NAMES = {
    1: "Ethereum",
    137: "Polygon",
    42161: "Arbitrum",
    10: "Optimism",
    8453: "Base",
    56: "BNB Chain",
    43114: "Avalanche",
}

# PairCreated event signature (same for Uniswap V2 forks)
PAIR_CREATED_EVENT_SIGNATURE = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"

# Uniswap V3 PoolCreated event signature
POOL_CREATED_EVENT_SIGNATURE = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"


def get_factory_address(chain_id: int, factory_name: str) -> str:
    """Get factory address for a specific chain and DEX"""
    chain_factories = FACTORY_ADDRESSES.get(chain_id, {})
    return chain_factories.get(factory_name.lower())


def get_all_factories(chain_id: int) -> dict:
    """Get all factories for a chain"""
    return FACTORY_ADDRESSES.get(chain_id, {})


def get_supported_chains() -> list:
    """Get list of supported chain IDs"""
    return list(CHAIN_NAMES.keys())


def get_chain_name(chain_id: int) -> str:
    """Get chain name from ID"""
    return CHAIN_NAMES.get(chain_id, f"Chain {chain_id}")
