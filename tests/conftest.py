import asyncio
import pytest_asyncio

from embit.transaction import Transaction

from .helpers import get_invoice

from boltz_client.boltz import BoltzConfig, BoltzClient


@pytest_asyncio.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def client():
    config = BoltzConfig(
        network="regtest",
        api_url="http://localhost:9001",
        mempool_url="http://localhost:8080/api",
        mempool_ws_url="ws://localhost:8080/api/v1/ws",
    )
    client = BoltzClient(config)
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
    invoice = get_invoice(10000, "pr-1")
    yield invoice["bolt11"]


@pytest_asyncio.fixture(scope="session")
async def pr_small():
    invoice = get_invoice(5000, "pr-2")
    yield invoice["bolt11"]


@pytest_asyncio.fixture(scope="session")
async def pr_refund():
    invoice = get_invoice(10001, "pr-3")
    yield invoice["bolt11"]
