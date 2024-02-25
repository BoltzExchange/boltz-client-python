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
