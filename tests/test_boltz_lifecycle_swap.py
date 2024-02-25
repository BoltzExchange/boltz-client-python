import asyncio

import pytest

from boltz_client.boltz import (
    BoltzClient,
    BoltzSwapResponse,
    BoltzSwapStatusException,
    BoltzSwapStatusResponse,
)

from .helpers import create_onchain_address, mine_blocks, pay_onchain, get_invoice


@pytest.mark.asyncio
async def test_create_swap_direction(client):
    amount = 110000
    swap_amount = client.substract_swap_fees(amount)
    invoice = get_invoice(swap_amount, "direction-test")
    _, swap = client.create_swap(invoice["bolt11"])
    assert swap.expectedAmount == amount


@pytest.mark.asyncio
async def test_create_swap_and_check_status(client, pr):
    refund_privkey_wif, swap = client.create_swap(pr)
    assert isinstance(refund_privkey_wif, str)
    assert isinstance(swap, BoltzSwapResponse)
    assert hasattr(swap, "id")
    assert hasattr(swap, "address")
    assert hasattr(swap, "expectedAmount")

    # combining those to test save creating an extra swap :)
    swap_status = client.swap_status(swap.id)
    assert isinstance(swap_status, BoltzSwapStatusResponse)
    assert hasattr(swap_status, "status")
    assert swap_status.status == "invoice.set"

    task = asyncio.create_task(client.wait_for_tx(swap.id))
    txid = pay_onchain(swap.address, swap.expectedAmount)
    await task

    assert txid, "txid is not None"

    swap_status_after_payment = client.swap_status(swap.id)
    assert swap_status_after_payment.status == "transaction.mempool"

    mine_blocks()
    await asyncio.sleep(1)

    swap_status_after_confirmed = client.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "transaction.claimed"


@pytest.mark.asyncio
async def test_create_swap_and_refund(client: BoltzClient, pr_refund):
    refund_privkey_wif, swap = client.create_swap(pr_refund)

    task = asyncio.create_task(client.wait_for_tx(swap.id))

    # pay to less onchain so the swap fails
    txid = pay_onchain(swap.address, swap.expectedAmount - 1000)
    assert txid, "txid is not None"

    await task

    mine_blocks()

    with pytest.raises(BoltzSwapStatusException):
        client.swap_status(swap.id)

    onchain_address = create_onchain_address()

    # wait for timeout
    mine_blocks(blocks=250)

    await asyncio.sleep(3)

    # actually refund
    txid = await client.refund_swap(
        boltz_id=swap.id,
        privkey_wif=refund_privkey_wif,
        lockup_address=swap.address,
        receive_address=onchain_address,
        redeem_script_hex=swap.redeemScript,
        timeout_block_height=swap.timeoutBlockHeight,
    )

    # check status
    try:
        client.swap_status(swap.id)
    except BoltzSwapStatusException as exc:
        assert exc.status == "swap.expired"
