import pytest

from boltz_client.boltz import BoltzClient, BoltzConfig, BoltzApiException
import logging
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_api_exception():
    config = BoltzConfig(network="regtest", api_url="http://localhost:9999", mempool_url="http://localhost:8080")
    with pytest.raises(BoltzApiException):
        BoltzClient(config)

@pytest.mark.asyncio
async def test_api_log_config(client):
    data = client.check_version()
    assert "version" in data
    assert data.get("version"), "3.1.5-dirty"
