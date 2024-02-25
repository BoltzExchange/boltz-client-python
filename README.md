# Boltz Python Client
Boltz Client in Python, implementing mainchain and liquid submarine swaps. Used by e.g. https://github.com/lnbits/boltz.

# CLI
```console
$ boltz --help
Usage: boltz [OPTIONS] COMMAND [ARGS]...

  Python CLI of boltz-client-python, enjoy submarine swapping. :)

Options:
  --help  Show this message and exit.

Commands:
  calculate-swap-send-amount     calculate the amount of the invoice you...
  claim-reverse-swap             claims a reverse swap
  create-reverse-swap            create a reverse swap
  create-reverse-swap-and-claim  create a reverse swap and claim
  create-swap                    create a swap boltz will pay your...
  refund-swap                    refund a swap
  show-pairs                     show pairs of possible assets to swap
  swap-status                    get swap status retrieves the status of...
```
install the latest release from [PyPI](https://pypi.org/project/boltz-client) via `pip install boltz_client`.

# LIB
### initialize the client
```python
from boltz_client import BoltzClient, BoltzConfig
config = BoltzConfig() # default config
client = BoltzClient(config, "BTC/BTC")
```
### lifecycle swap
```python
pr = create_lightning_invoice(100000) # example function to create a lightning invoice
refund_privkey_wif, swap = client.create_swap(pr)
print(f"pay this amount: {swap.expectedAmount}")
print(f"to this address: {swap.address}")
# when you pay the amount the invoice will be settled after the boltz claimed the swap
```
if swap fails you can refund like this
```python
# example function to create an onchain address
onchain_address = create_onchain_address()
txid = await client.refund_swap(
    boltz_id=swap.id,
    privkey_wif=refund_privkey_wif,
    lockup_address=swap.address,
    receive_address=onchain_address,
    redeem_script_hex=swap.redeemScript,
    timeout_block_height=swap.timeoutBlockHeight,
)
```

### lifecycle reverse swap
```python
claim_privkey_wif, preimage_hex, swap = client.create_reverse_swap(50000)
# example function to pay the invoice
pay_task = asyncio.create_task(pay_invoice(swap.invoice))
# example function to create an onchain address
new_address = create_onchain_address()
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
txid = await task
await pay_task
```


# development

## installing
```console
poetry install
```

## running cli
```console
poetry run boltz
```

## starting regtest
```console
cd docker
chmod +x regtest
./regtest
```

## running tests
```console
poetry run pytest
```
