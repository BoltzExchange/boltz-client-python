import pytest
import asyncio

from boltz_client.boltz import (
    BoltzClient,
    BoltzReverseSwapResponse,
    BoltzSwapStatusResponse,
)

from .helpers import pay_invoice, mine_blocks, create_onchain_address


@pytest.mark.asyncio
async def test_create_reverse_swap_and_claim(client: BoltzClient):
    claim_privkey_wif, preimage_hex, swap = client.create_reverse_swap(10000)
    assert type(claim_privkey_wif) == str
    assert type(preimage_hex) == str
    assert type(swap) == BoltzReverseSwapResponse
    assert hasattr(swap, "id")
    assert hasattr(swap, "invoice")
    assert hasattr(swap, "redeemScript")
    assert hasattr(swap, "lockupAddress")
    assert hasattr(swap, "timeoutBlockHeight")
    assert hasattr(swap, "onchainAmount")

    # # combining those to test save creating an extra swap :)
    swap_status = client.swap_status(swap.id)
    assert type(swap_status) == BoltzSwapStatusResponse
    assert hasattr(swap_status, "status")
    assert swap_status.status == "swap.created"

    # create_task is used because pay_invoice is stuck as long as boltz does not
    # see the onchain claim tx and it ends up in deadlock
    p = pay_invoice(swap.invoice)

    # check if pay_invoice is done / fails first
    # outs, _ = p.communicate()
    if p.poll():
    #     data = json.loads(outs.decode("UTF-8"))
    #     logging.error(data.get("message"))
    #     get_lockup_task.cancel()
        assert False

    new_address = create_onchain_address()
    txid = await client.claim_reverse_swap(
        receive_address=new_address,
        lockup_address=swap.lockupAddress,
        redeem_script_hex=swap.redeemScript,
        privkey_wif=claim_privkey_wif,
        preimage_hex=preimage_hex,
        zeroconf=True,
    )

    task = asyncio.create_task(client.mempool.wait_for_tx_confirmed(txid))
    mine_blocks()
    await task

    swap_status_after_confirmed = client.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "invoice.settled"

    # wait for invoice going through
    p.wait()
