""" boltz_client test helpers """

import json
import time
from subprocess import PIPE, Popen, run

docker_bitcoin_rpc = "boltz"
docker_prefix = "boltz-client"
docker_cmd = "docker exec"
is_compose_v2 = None  # Set to True/False depending on docker compose version

def run_cmd(cmd: str) -> str:
    return run(cmd, shell=True, capture_output=True).stdout.decode("UTF-8").strip()


def get_docker_cmd(image: str, cmd: str) -> str:
    global is_compose_v2
    if is_compose_v2 is None:
        is_compose_v2 = 'Compose' in run_cmd("docker --help")
    suffix = f"-{image}-1" if is_compose_v2 else f"_{image}_1"
    return f"{docker_cmd} {docker_prefix}{suffix} {cmd}"

docker_lightning = f"corelightning"
docker_lightning_cli = f"lightning-cli --network regtest"

docker_bitcoin = f"bitcoind"
docker_bitcoin_cli = f"bitcoin-cli -rpcuser={docker_bitcoin_rpc} -rpcpassword={docker_bitcoin_rpc} -regtest"

docker_elements = f"elementsd"
docker_elements_cli = f"elements-cli -rpcuser={docker_bitcoin_rpc} -rpcpassword={docker_bitcoin_rpc}"


def get_invoice(sats: int, prefix: str, description: str = "test") -> dict:
    msats = sats * 1000
    cli_cmd = f"invoice {msats} {prefix}-{time.time()} {description}"
    cmd = get_docker_cmd(docker_lightning, f"{docker_lightning_cli} {cli_cmd}")
    return json.loads(run_cmd(cmd))


def pay_invoice(invoice: str) -> Popen:
    cli_cmd = f"pay {invoice}"
    cmd = get_docker_cmd(docker_lightning, f"{docker_lightning_cli} {cli_cmd}")
    return Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE)


def run_core_cli_cmd(pair: str, cli_cmd: str) -> str:
    if pair == "L-BTC/BTC":
        cmd = get_docker_cmd(docker_elements, f"{docker_elements_cli} {cli_cmd}")
    else:
        cmd = get_docker_cmd(docker_bitcoin, f"{docker_bitcoin_cli} {cli_cmd}")
    return run_cmd(cmd)

def mine_blocks(pair: str = "BTC/BTC", blocks: int = 1) -> str:
    return run_core_cli_cmd(pair, f"-generate {blocks}")


def create_onchain_address(pair: str = "BTC/BTC", address_type: str = "bech32") -> str:
    return run_core_cli_cmd(pair, f"getnewaddress {address_type}")


def pay_onchain(address: str, sats: int, pair: str = "BTC/BTC") -> str:
    btc = sats / 10**8
    return run_core_cli_cmd(pair, f"sendtoaddress {address} {btc}")
