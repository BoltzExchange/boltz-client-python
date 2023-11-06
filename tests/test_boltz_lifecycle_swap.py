import asyncio

import pytest

from boltz_client.boltz import (
    BoltzClient,
    BoltzSwapResponse,
    BoltzSwapStatusException,
    BoltzSwapStatusResponse,
)
from boltz_client.mempool import MempoolBlockHeightException

from .helpers import create_onchain_address, mine_blocks, pay_onchain


@pytest.mark.asyncio
async def test_create_swap_and_check_status(client, pr):
    refund_privkey_wif, swap = client.create_swap(pr)
    assert type(refund_privkey_wif) == str
    assert type(swap) == BoltzSwapResponse
    assert hasattr(swap, "id")
    assert hasattr(swap, "address")
    assert hasattr(swap, "expectedAmount")

    # combining those to test save creating an extra swap :)
    swap_status = client.swap_status(swap.id)
    assert type(swap_status) == BoltzSwapStatusResponse
    assert hasattr(swap_status, "status")
    assert swap_status.status == "invoice.set"

    task = asyncio.create_task(client.mempool.wait_for_lockup_tx(swap.address))
    txid = pay_onchain(swap.address, swap.expectedAmount)
    await task

    swap_status_after_payment = client.swap_status(swap.id)
    assert swap_status_after_payment.status == "transaction.mempool"

    task = asyncio.create_task(client.mempool.wait_for_tx_confirmed(txid))
    mine_blocks()
    await task

    swap_status_after_confirmed = client.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "transaction.claimed"


@pytest.mark.asyncio
async def test_create_swap_and_refund(client: BoltzClient, pr_refund):
    refund_privkey_wif, swap = client.create_swap(pr_refund)

    task = asyncio.create_task(client.mempool.wait_for_lockup_tx(swap.address))

    # pay to less onchain so the swap fails
    txid = pay_onchain(swap.address, swap.expectedAmount - 1000)

    await task

    task = asyncio.create_task(client.mempool.wait_for_tx_confirmed(txid))
    mine_blocks()
    await task

    with pytest.raises(BoltzSwapStatusException):
        client.swap_status(swap.id)

    onchain_address = create_onchain_address()

    # try refund before timeout
    with pytest.raises(MempoolBlockHeightException):
        await client.refund_swap(
            boltz_id=swap.id,
            privkey_wif=refund_privkey_wif,
            lockup_address=swap.address,
            receive_address=onchain_address,
            redeem_script_hex=swap.redeemScript,
            timeout_block_height=swap.timeoutBlockHeight,
        )

    # wait for timeout
    blocks_to_mine = swap.timeoutBlockHeight - client.mempool.get_blockheight() + 3
    mine_blocks(blocks=blocks_to_mine)

    # actually refund
    txid = await client.refund_swap(
        boltz_id=swap.id,
        privkey_wif=refund_privkey_wif,
        lockup_address=swap.address,
        receive_address=onchain_address,
        redeem_script_hex=swap.redeemScript,
        timeout_block_height=swap.timeoutBlockHeight,
    )

    task = asyncio.create_task(client.mempool.wait_for_tx_confirmed(txid))
    mine_blocks()
    await task

    # check status
    try:
        client.swap_status(swap.id)
    except BoltzSwapStatusException as exc:
        assert exc.status == "swap.expired"
