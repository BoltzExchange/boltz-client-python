import asyncio
import pytest

from boltz_client.boltz import (
    BoltzClient,
    BoltzSwapStatusException,
)
from boltz_client.mempool import MempoolBlockHeightException
from .helpers import create_onchain_address, mine_blocks, pay_onchain


@pytest.mark.asyncio
async def test_create_swap_and_check_status(client_liquid: BoltzClient, liquid_pr):
    _, swap = client_liquid.create_swap(liquid_pr)

    _ = pay_onchain(swap.address, swap.expectedAmount, client_liquid.pair)

    await asyncio.sleep(1)

    swap_status_after_payment = client_liquid.swap_status(swap.id)
    assert swap_status_after_payment.status == "transaction.mempool"

    mine_blocks(client_liquid.pair)

    await asyncio.sleep(1)

    swap_status_after_confirmed = client_liquid.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "transaction.claimed"


@pytest.mark.asyncio
async def test_create_swap_and_refund(client_liquid: BoltzClient, liquid_pr_refund):
    refund_privkey_wif, swap = client_liquid.create_swap(liquid_pr_refund)

    # pay to less onchain so the swap fails
    _ = pay_onchain(swap.address, swap.expectedAmount - 1000, client_liquid.pair)

    await asyncio.sleep(1)
    mine_blocks(client_liquid.pair)
    await asyncio.sleep(1)

    with pytest.raises(BoltzSwapStatusException):
        client_liquid.swap_status(swap.id)

    onchain_address = create_onchain_address(client_liquid.pair)

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
    blocks_to_mine = swap.timeoutBlockHeight - client_liquid.mempool.get_blockheight() + 10
    mine_blocks(pair=client_liquid.pair, blocks=blocks_to_mine)

    await asyncio.sleep(10)

    # actually refund
    _ = await client_liquid.refund_swap(
        boltz_id=swap.id,
        privkey_wif=refund_privkey_wif,
        lockup_address=swap.address,
        receive_address=onchain_address,
        redeem_script_hex=swap.redeemScript,
        timeout_block_height=swap.timeoutBlockHeight,
        blinding_key=swap.blindingKey,
    )

    mine_blocks(pair=client_liquid.pair)
    await asyncio.sleep(1)

    # check status
    try:
        client_liquid.swap_status(swap.id)
    except BoltzSwapStatusException as exc:
        assert exc.status == "swap.expired"
