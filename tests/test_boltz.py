import pytest
import logging
logger = logging.getLogger(__name__)


from boltz_client.boltz import (
    BoltzClient,
    BoltzConfig,
    BoltzApiException,
    BoltzLimitException,
    BoltzNotFoundException,
)


@pytest.mark.asyncio
async def test_api_exception():
    config = BoltzConfig(
        network="regtest",
        api_url="http://localhost:9999",
        mempool_url="http://localhost:8080"
    )
    with pytest.raises(BoltzApiException):
        BoltzClient(config)


@pytest.mark.asyncio
async def test_api_log_config(client):
    data = client.check_version()
    assert "version" in data
    assert data.get("version") == "3.1.5-dirty"


@pytest.mark.asyncio
async def test_check_if_limits_are_set(client):
    assert client.limit_minimal == 10000
    assert client.limit_maximal == 4294967


@pytest.mark.asyncio
async def test_check_min_limit(client):
    client.check_limits(10000)


@pytest.mark.asyncio
async def test_check_below_min_limit(client):
    with pytest.raises(BoltzLimitException):
        client.check_limits(9999)


@pytest.mark.asyncio
async def test_check_max_limit(client):
    client.check_limits(4294967)


@pytest.mark.asyncio
async def test_check_below_max_limit(client):
    with pytest.raises(BoltzLimitException):
        client.check_limits(4294968)


@pytest.mark.asyncio
async def test_swap_status_invalid(client):
    with pytest.raises(BoltzNotFoundException):
        client.swap_status("INVALID")


@pytest.mark.asyncio
async def test_create_swap_invalid_payment_request(client):
    with pytest.raises(BoltzApiException):
        _ = client.create_swap("lnbrc1000000", 10000)
