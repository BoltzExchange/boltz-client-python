import asyncio
import pytest

from boltz_client.boltz import (
    BoltzClient,
    BoltzSwapStatusException,
)
from boltz_client.mempool import MempoolBlockHeightException
from .helpers import create_onchain_address, mine_blocks, pay_onchain


@pytest.mark.asyncio
@pytest.mark.skip
async def test_create_swap_and_check_status(client_liquid: BoltzClient, pr):
    _, swap = client_liquid.create_swap(pr)

    _ = pay_onchain(swap.address, swap.expectedAmount, client_liquid.pair)

    await asyncio.sleep(1)

    swap_status_after_payment = client_liquid.swap_status(swap.id)
    assert swap_status_after_payment.status == "transaction.mempool"

    mine_blocks(client_liquid.pair)

    await asyncio.sleep(1)

    swap_status_after_confirmed = client_liquid.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "transaction.claimed"


@pytest.mark.asyncio
async def test_create_swap_and_refund(client_liquid: BoltzClient, pr_refund):
    refund_privkey_wif, swap = client_liquid.create_swap(pr_refund)

    # pay to less onchain so the swap fails
    txid = pay_onchain(swap.address, swap.expectedAmount - 1000, client_liquid.pair)
    print("txid", txid)

    await asyncio.sleep(1)

    mine_blocks(client_liquid.pair)
    await asyncio.sleep(1)

    with pytest.raises(BoltzSwapStatusException):
        client_liquid.swap_status(swap.id)

    onchain_address = create_onchain_address(client_liquid.pair)
    print("onchain_address", onchain_address)

    # try refund before timeout
    with pytest.raises(MempoolBlockHeightException):
        await client_liquid.refund_swap(
            boltz_id=swap.id,
            privkey_wif=refund_privkey_wif,
            lockup_address=swap.address,
            receive_address=onchain_address,
            redeem_script_hex=swap.redeemScript,
            timeout_block_height=swap.timeoutBlockHeight,
            blinding_key=swap.blindingKey,
        )

    # wait for timeout
    blocks_to_mine = swap.timeoutBlockHeight - client_liquid.mempool.get_blockheight() + 3
    print("blocks_to_mine", blocks_to_mine)
    mine_blocks(pair=client_liquid.pair, blocks=blocks_to_mine)
    await asyncio.sleep(5)

    # actually refund
    txid_refund = await client_liquid.refund_swap(
        boltz_id=swap.id,
        privkey_wif=refund_privkey_wif,
        lockup_address=swap.address,
        receive_address=onchain_address,
        redeem_script_hex=swap.redeemScript,
        timeout_block_height=swap.timeoutBlockHeight,
        blinding_key=swap.blindingKey,
    )
    print("txid_refund", txid_refund)

    mine_blocks(pair=client_liquid.pair)
    await asyncio.sleep(1)

    # check status
    try:
        client_liquid.swap_status(swap.id)
    except BoltzSwapStatusException as exc:
        assert exc.status == "swap.expired"
