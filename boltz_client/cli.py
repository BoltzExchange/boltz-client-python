import click

from boltz_client.boltz import BoltzConfig, BoltzClient, BoltzCreateSwapResponse


config = BoltzConfig(
    network="regtest",
    api_url="http://localhost:9001",
    mempool_url="http://localhost:8080"
)

@click.group()
def command_group():
    """Python CLI of boltz-client-python, enjoy submarine swapping. :)"""


def wrapper(*args, func_name: str):
    client = BoltzClient(config)
    func = getattr(client, func_name)
    return func(*args)


@click.command()
@click.argument('sats', type=int)
@click.argument('payment_request', type=str)
def create_swap(sats, payment_request):
    """
    create a swap
    boltz will pay your invoice after you paid the onchain address

    SATS you want to swap, has to be the same as in PAYMENT_REQUEST
    PAYMENT_REQUEST with the same amount as specified in SATS
    """
    privkey_wif, res = wrapper(sats, payment_request, func_name="create_swap")
    click.echo(f"preimage of swap in wif: {privkey_wif}")
    click.echo(res)


@click.command()
def create_reverse_swap():
    """
    create a reverse swap
    """


@click.command()
@click.argument('id', type=str)
def swap_status(id):
    """
    get swap status
    retrieves the status of your boltz swap from the api

    ID is the id of your boltz swap
    """
    data = wrapper(id, func_name="swap_status")
    click.echo(data)


@click.command()
def version():
    """ shows version of boltz api """
    data = wrapper(func_name="check_version")
    click.echo(data["version"])


def main():
    command_group.add_command(swap_status)
    command_group.add_command(create_swap)
    command_group.add_command(create_reverse_swap)
    command_group.add_command(version)
    command_group()


if __name__ == "__main__":
    main()
