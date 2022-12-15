import pytest

from boltz_client.mempool import MempoolApiException
from boltz_client.boltz import BoltzClient, BoltzConfig


@pytest.mark.asyncio
async def test_api_exception():
    config = BoltzConfig(network="regtest", api_url="http://localhost:9001", mempool_url="http://localhost:8888")
    with pytest.raises(MempoolApiException):
        BoltzClient(config)


@pytest.mark.asyncio
async def test_blockheight(client):
    blockheight = client.mempool.get_blockheight()
    assert type(blockheight) == int
    assert blockheight == 170


@pytest.mark.asyncio
async def test_fees(client):
    fees = client.mempool.get_fees()
    assert type(fees) == int
    assert fees == 1


@pytest.mark.asyncio
async def test_fee_estimation(client):
    fees = client.mempool.get_fee_estimation()
    assert type(fees) == int
    assert fees == 200


@pytest.mark.asyncio
async def test_send_invalid_onchain(client, raw_tx_invalid):
    with pytest.raises(MempoolApiException):
        client.mempool.send_onchain_tx(raw_tx_invalid)


# @pytest.mark.asyncio
# async def test_send_valid_onchain(client, raw_tx):
#     sent = client.mempool.send_onchain_tx(raw_tx)
#     print(sent)
