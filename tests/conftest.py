import asyncio
import pytest_asyncio

from binascii import hexlify
from embit.transaction import Transaction

from boltz_client.boltz import BoltzConfig, BoltzClient


@pytest_asyncio.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def client():
    config = BoltzConfig(network="regtest", api_url="http://localhost:9001", mempool_url="http://localhost:8080")
    client = BoltzClient(config)
    yield client


@pytest_asyncio.fixture(scope="session")
async def raw_tx_invalid():
    tx = Transaction()
    raw_tx = hexlify(tx.serialize())
    yield raw_tx


@pytest_asyncio.fixture(scope="session")
async def raw_tx():
    tx = Transaction()
    raw_tx = hexlify(tx.serialize())
    yield raw_tx
