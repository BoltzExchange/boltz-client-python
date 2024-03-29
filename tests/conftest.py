import asyncio

import pytest_asyncio
from embit.transaction import Transaction

from boltz_client.boltz import BoltzClient, BoltzConfig

from .helpers import get_invoice

config = BoltzConfig(
    pairs=["BTC/BTC", "L-BTC/BTC"],
    network="regtest",
    network_liquid="elementsregtest",
    api_url="http://localhost:9001",
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def client():
    client = BoltzClient(config)
    yield client


@pytest_asyncio.fixture(scope="session")
async def client_liquid():
    client = BoltzClient(config, pair="L-BTC/BTC")
    yield client


@pytest_asyncio.fixture(scope="session")
async def raw_tx_invalid():
    tx = Transaction()
    raw_tx = bytes.hex(tx.serialize())
    yield raw_tx


@pytest_asyncio.fixture(scope="session")
async def raw_tx():
    tx = Transaction()
    raw_tx = bytes.hex(tx.serialize())
    yield raw_tx


@pytest_asyncio.fixture(scope="session")
async def pr():
    invoice = get_invoice(50000, "pr-1")
    yield invoice["bolt11"]


@pytest_asyncio.fixture(scope="session")
async def pr_small():
    invoice = get_invoice(5000, "pr-2")
    yield invoice["bolt11"]


@pytest_asyncio.fixture(scope="session")
async def pr_refund():
    invoice = get_invoice(50001, "pr-3")
    yield invoice["bolt11"]


@pytest_asyncio.fixture(scope="session")
async def liquid_pr():
    invoice = get_invoice(55555, "liquid-pr-1")
    yield invoice["bolt11"]


@pytest_asyncio.fixture(scope="session")
async def liquid_pr_refund():
    invoice = get_invoice(50001, "liquid-pr-2")
    yield invoice["bolt11"]
