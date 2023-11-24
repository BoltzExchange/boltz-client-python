import pytest

from boltz_client.boltz import BoltzClient, BoltzConfig
from boltz_client.mempool import MempoolApiException, MempoolBlockHeightException


@pytest.mark.asyncio
async def test_api_exception():
    config = BoltzConfig(
        network="regtest",
        api_url="http://localhost:9001",
        mempool_url="http://localhost:8888",
    )
    with pytest.raises(MempoolApiException):
        BoltzClient(config)


@pytest.mark.asyncio
async def test_blockheight(client):
    blockheight = client.mempool.get_blockheight()
    assert isinstance(blockheight, int)


@pytest.mark.asyncio
async def test_check_blockheight_exception(client):
    with pytest.raises(MempoolBlockHeightException):
        blockheight = client.mempool.get_blockheight()
        client.mempool.check_block_height(blockheight + 1)


@pytest.mark.asyncio
async def test_check_blockheight(client):
    blockheight = client.mempool.get_blockheight()
    client.mempool.check_block_height(blockheight)


@pytest.mark.asyncio
async def test_fees(client):
    fees = client.mempool.get_fees()
    assert isinstance(fees, int)
    assert fees == 1


@pytest.mark.asyncio
async def test_send_invalid_onchain(client, raw_tx_invalid):
    with pytest.raises(MempoolApiException):
        client.mempool.send_onchain_tx(raw_tx_invalid)
