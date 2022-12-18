import os
import time
import json


docker_bitcoin_rpc = "boltz"
docker_prefix = "boltz-client"
docker_cmd = f"docker exec"

docker_lightning = f"{docker_cmd} {docker_prefix}-corelightning-1"
docker_lightning_cli = f"{docker_lightning} lightning-cli --network regtest"

docker_bitcoin = f"{docker_cmd} {docker_prefix}-bitcoind-1"
docker_bitcoin_cli = f"{docker_bitcoin} bitcoin-cli -rpcuser={docker_bitcoin_rpc} -rpcpassword={docker_bitcoin_rpc} -regtest"


def run_cmd(cmd: str) -> str:
    return os.popen(cmd).read().strip()


def run_cmd_json(cmd: str) -> dict:
    return json.loads(run_cmd(cmd))


def get_invoice(sats: int, prefix: str, description: str = "test") -> dict:
    msats = sats * 1000
    return run_cmd_json(f"{docker_lightning_cli} invoice {msats} {prefix}-{time.time()} {description}")


def mine_blocks(blocks: int = 1) -> str:
    return run_cmd(f"{docker_bitcoin_cli} -generate {blocks}")


def get_address(address_type: str = "bech32") -> str:
    return run_cmd(f"{docker_bitcoin_cli} getnewaddress {address_type}")


def pay_onchain(address: str, sats: int) -> str:
    btc = sats * 0.00000001
    return run_cmd(f"{docker_bitcoin_cli} sendtoaddress {address} {btc}")
