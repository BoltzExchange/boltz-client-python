import pytest

from boltz_client.mempool import LockupData
from boltz_client.onchain import create_onchain_tx


@pytest.mark.asyncio
async def test_psbt():

    txid, rawtx, psbt = create_onchain_tx(
        lockup_tx=LockupData(script_pub_key="bcrt1qjqnmqsv43kefwsjtky7z3ece5unesyemmpk3nhr2xscqrwtqqq2qd74xw6", status='unconfirmed', txid='9d63f812b44817bb78b34650418ee6e77244c30b496399594bc48ef3c7d0d73f', vout_cnt=0, vout_amount=39494),
        receive_address="bcrt1qqgytgy08ffx5raxu2awxut57gd8krlutu4f3qs",
        privkey_wif="cTkUkG2xXkt7Wg6XnAM3aAyWmZkiS8okcqBXD6iY6td2ACVNZ2VE",
        redeem_script_hex="8201208763a91448c0ef1e2834b052376534d85be0182dd05373518821028553d74fa14fab1c3c7d676fcb37992b67b35583efcdeba2b8574cae3e9c1f8d6775023b01b17521025613458aa9aa232f410d519ea8fb1d021fb91f07bea72cafe01db9bfb5fbcc7468ac",
        fees=200,
        pair="BTC/BTC",
        sequence = 4294967295,
        timeout_block_height = 0,
        preimage_hex = "d8770b2d6bedfa8200366337efe0916d2a89375ef6222e001ffb472aceba5619",
        script_sig = None,
    )

    print(txid)
    print(rawtx)
    print(psbt)

    assert False

@pytest.mark.asyncio
async def test_esbt():

    txid, rawtx, psbt = create_onchain_tx(
        lockup_tx=LockupData(script_pub_key="bcrt1qjqnmqsv43kefwsjtky7z3ece5unesyemmpk3nhr2xscqrwtqqq2qd74xw6", status='unconfirmed', txid='9d63f812b44817bb78b34650418ee6e77244c30b496399594bc48ef3c7d0d73f', vout_cnt=0, vout_amount=39494),
        receive_address="bcrt1qqgytgy08ffx5raxu2awxut57gd8krlutu4f3qs",
        privkey_wif="cTkUkG2xXkt7Wg6XnAM3aAyWmZkiS8okcqBXD6iY6td2ACVNZ2VE",
        redeem_script_hex="8201208763a91448c0ef1e2834b052376534d85be0182dd05373518821028553d74fa14fab1c3c7d676fcb37992b67b35583efcdeba2b8574cae3e9c1f8d6775023b01b17521025613458aa9aa232f410d519ea8fb1d021fb91f07bea72cafe01db9bfb5fbcc7468ac",
        fees=200,
        pair="L-BTC/BTC",
        sequence = 4294967295,
        timeout_block_height = 0,
        preimage_hex = "d8770b2d6bedfa8200366337efe0916d2a89375ef6222e001ffb472aceba5619",
        script_sig = None,
    )

    print(txid)
    print(rawtx)
    print(psbt)

    assert False
