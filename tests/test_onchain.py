import pytest

from boltz_client.onchain import validate_address


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr, network",
    [
        ("bc1asdkljalskdj", "main"),
        ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "test"),
        ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "regtest"),
        ("bcrt1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "regtest"),
        ("026165850492521f4ac8abd9bd8088123446d126f648ca35e60f88177dc149ceb2", "main"),
    ],
)
async def test_invalid_address(addr, network):
    with pytest.raises(ValueError):
        validate_address(addr, network)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr, network",
    [
        ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "main"),
        ("bcrt1qky0es27zfejlr3grpfl4pj47w7yfm0atwqdf3y", "regtest"),
        ("bcrt1pataahlktd49l33ee62k62exl7rwuhefgyyzpx8axecgxq36upxcshjsssq", "regtest"),
    ],
)
async def test_valid_address(addr, network):
    validate_address(addr, network)
