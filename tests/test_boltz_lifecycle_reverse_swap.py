import asyncio

import pytest

from boltz_client.boltz import (
    BoltzClient,
    BoltzReverseSwapResponse,
    BoltzSwapStatusResponse,
)

from .helpers import create_onchain_address, mine_blocks, pay_invoice


@pytest.mark.asyncio
async def test_create_reverse_swap_and_claim(client: BoltzClient):
    claim_privkey_wif, preimage_hex, swap = client.create_reverse_swap(50000)
    assert isinstance(claim_privkey_wif, str)
    assert isinstance(preimage_hex, str)
    assert isinstance(swap, BoltzReverseSwapResponse)
    assert hasattr(swap, "id")
    assert hasattr(swap, "invoice")
    assert hasattr(swap, "redeemScript")
    assert hasattr(swap, "lockupAddress")
    assert hasattr(swap, "timeoutBlockHeight")
    assert hasattr(swap, "onchainAmount")

    # # combining those to test save creating an extra swap :)
    swap_status = client.swap_status(swap.id)
    assert isinstance(swap_status, BoltzSwapStatusResponse)
    assert hasattr(swap_status, "status")
    assert swap_status.status == "swap.created"

    # create_task is used because pay_invoice is stuck as long as boltz does not
    # see the onchain claim tx and it ends up in deadlock
    p = pay_invoice(swap.invoice)

    # check if pay_invoice is done / fails first
    if p.poll():
        assert False

    new_address = create_onchain_address(client.pair)

    task = asyncio.create_task(client.claim_reverse_swap(
        boltz_id=swap.id,
        receive_address=new_address,
        lockup_address=swap.lockupAddress,
        redeem_script_hex=swap.redeemScript,
        blinding_key=swap.blindingKey,
        privkey_wif=claim_privkey_wif,
        preimage_hex=preimage_hex,
        zeroconf=True,
    ))

    mine_blocks()

    txid = await task

    assert txid, "txid is not None"

    swap_status_after_confirmed = client.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "invoice.settled"
    # wait for invoice going through
    p.wait()


@pytest.mark.asyncio
async def test_create_reverse_swap_direction(client: BoltzClient):
    amount = 1100000
    swap_amount = client.add_reverse_swap_fees(amount)
    claim_privkey_wif, preimage_hex, swap = client.create_reverse_swap(swap_amount)

    p = pay_invoice(swap.invoice)

    # check if pay_invoice is done / fails first
    if p.poll():
        assert False
    new_address = create_onchain_address(client.pair)
    txid = await client.claim_reverse_swap(
        boltz_id=swap.id,
        receive_address=new_address,
        lockup_address=swap.lockupAddress,
        redeem_script_hex=swap.redeemScript,
        blinding_key=swap.blindingKey,
        privkey_wif=claim_privkey_wif,
        preimage_hex=preimage_hex,
        zeroconf=True,
    )
    mine_blocks()

    assert txid, "txid is not None"

    # wait for invoice going through
    p.wait()
