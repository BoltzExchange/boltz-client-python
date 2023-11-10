import asyncio
import pytest

from boltz_client.boltz import BoltzClient
from .helpers import create_onchain_address, mine_blocks, pay_invoice


@pytest.mark.asyncio
async def test_liquid_create_reverse_swap_and_claim(client_liquid: BoltzClient):
    claim_privkey_wif, preimage_hex, swap = client_liquid.create_reverse_swap(10000)

    # create_task is used because pay_invoice is stuck as long as boltz does not
    # see the onchain claim tx and it ends up in deadlock
    p = pay_invoice(swap.invoice)

    # check if pay_invoice is done / fails first
    if p.poll():
        assert False

    new_address = create_onchain_address(client_liquid.pair)
    txid = await client_liquid.claim_reverse_swap(
        boltz_id=swap.id,
        receive_address=new_address,
        lockup_address=swap.lockupAddress,
        redeem_script_hex=swap.redeemScript,
        blinding_key=swap.blindingKey,
        privkey_wif=claim_privkey_wif,
        preimage_hex=preimage_hex,
        zeroconf=True,
    )

    task = asyncio.create_task(client_liquid.mempool.wait_for_tx_confirmed(txid))
    mine_blocks(client_liquid.pair)
    await task

    swap_status_after_confirmed = client_liquid.swap_status(swap.id)
    assert swap_status_after_confirmed.status == "invoice.settled"
    # wait for invoice going through
    p.wait()
