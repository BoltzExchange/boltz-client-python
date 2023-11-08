""" boltz_client onchain module """
import os
from hashlib import sha256
from typing import Optional

from embit import ec, script
from embit.base import EmbitError
from embit.liquid.addresses import addr_decode
from embit.liquid.networks import NETWORKS as LNETWORKS
from embit.liquid.pset import PSET
from embit.liquid.transaction import LTransaction, LTransactionInput, LTransactionOutput
from embit.networks import NETWORKS
from embit.psbt import PSBT
# from embit.liquid.finalizer import finalize_psbt
from embit.transaction import SIGHASH, Transaction, TransactionInput, TransactionOutput

from .mempool import LockupData

LASSET = bytes.fromhex("5ac9f65c0efcc4775e0baec4ec03abdde22473cd3cf33c0419ca290e0751b225")


def get_txid(tx_hex: str) -> str:
    try:
        tx = Transaction.from_string(tx_hex)
        return tx.txid().hex()
    except EmbitError as exc:
        raise ValueError("Invalid transaction hex") from exc


def validate_address(address: str, network: str, pair: str):
    if pair == "L-BTC/BTC":
        net = LNETWORKS[network]
    else:
        net = NETWORKS[network]
    try:
        addr = script.Script.from_address(address) or script.Script()
        if addr.address(net) != address:
            raise ValueError("Invalid network")
    except EmbitError as exc:
        raise ValueError(f"Invalid address: {exc}") from exc


def create_preimage() -> tuple[str, str]:
    preimage = os.urandom(32)
    preimage_hash = sha256(preimage).hexdigest()
    return preimage.hex(), preimage_hash


def create_key_pair(network, pair) -> tuple[str, str]:
    if pair == "L-BTC/BTC":
        net = LNETWORKS[network]
    else:
        net = NETWORKS[network]

    privkey = ec.PrivateKey(os.urandom(32), True, net)
    pubkey_hex = bytes.hex(privkey.sec())
    privkey_wif = privkey.wif(net)
    return privkey_wif, pubkey_hex


def create_refund_tx(
    privkey_wif: str,
    receive_address: str,
    redeem_script_hex: str,
    timeout_block_height: int,
    lockup_tx: LockupData,
    pair: str,
    fees: int,
    blinding_key: Optional[str] = None,
) -> tuple[str, str, str]:
    # encrypt redeemscript to script_sig
    rs = bytes([34]) + bytes([0]) + bytes([32])
    rs += sha256(bytes.fromhex(redeem_script_hex)).digest()
    script_sig = script.Script(data=rs)
    return create_onchain_tx(
        sequence=0xFFFFFFFE,
        redeem_script_hex=redeem_script_hex,
        privkey_wif=privkey_wif,
        lockup_tx=lockup_tx,
        receive_address=receive_address,
        timeout_block_height=timeout_block_height,
        script_sig=script_sig,
        pair=pair,
        fees=fees,
        blinding_key=blinding_key,
    )


def create_claim_tx(
    preimage_hex: str,
    privkey_wif: str,
    receive_address: str,
    redeem_script_hex: str,
    lockup_tx: LockupData,
    fees: int,
    pair: str,
    blinding_key: Optional[str] = None,
) -> tuple[str, str, str]:
    return create_onchain_tx(
        preimage_hex=preimage_hex,
        lockup_tx=lockup_tx,
        receive_address=receive_address,
        privkey_wif=privkey_wif,
        redeem_script_hex=redeem_script_hex,
        fees=fees,
        pair=pair,
        blinding_key=blinding_key,
    )


def create_onchain_tx(
    lockup_tx: LockupData,
    receive_address: str,
    privkey_wif: str,
    redeem_script_hex: str,
    fees: int,
    pair: str,
    sequence: int = 0xFFFFFFFF,
    timeout_block_height: int = 0,
    preimage_hex: str = "",
    script_sig: Optional[script.Script] = None,
    blinding_key: Optional[str] = None,
) -> tuple[str, str, str]:

    TxInput = LTransactionInput if pair == "L-BTC/BTC" else TransactionInput
    Tx = LTransaction if pair == "L-BTC/BTC" else Transaction
    Partial = PSET if pair == "L-BTC/BTC" else PSBT

    if pair == "L-BTC/BTC":
        if not blinding_key:
            raise ValueError("Blinding key is required for L-BTC/BTC pair")
        lockup_transaction = LTransaction.from_string(lockup_tx.tx)
        value, *_ = lockup_transaction.vout[lockup_tx.vout_cnt].unblind(bytes.fromhex(blinding_key))
        lockup_tx.vout_amount = value
        _, pubkey = addr_decode(receive_address)
        vout = LTransactionOutput(
            asset=LASSET,
            value=lockup_tx.vout_amount - fees,
            script_pubkey=script.address_to_scriptpubkey(receive_address),
            ecdh_pubkey=pubkey,
        )
        witness_utxo = LTransactionOutput(
            asset=LASSET,
            value=lockup_tx.vout_amount,
            script_pubkey=script.address_to_scriptpubkey(lockup_tx.script_pub_key),
            ecdh_pubkey=pubkey,
        )
    else:
        vout = TransactionOutput(
            lockup_tx.vout_amount - fees,
            script.address_to_scriptpubkey(receive_address),
        )
        witness_utxo = TransactionOutput(
            lockup_tx.vout_amount,
            script.address_to_scriptpubkey(lockup_tx.script_pub_key),
        )

    vin = TxInput(bytes.fromhex(lockup_tx.txid), lockup_tx.vout_cnt, sequence=sequence)
    tx = Tx(vin=[vin], vout=[vout])
    if timeout_block_height > 0:
        tx.locktime = timeout_block_height

    redeem_script = script.Script(data=bytes.fromhex(redeem_script_hex))
    h = tx.sighash_segwit(0, redeem_script, lockup_tx.vout_amount)
    sig = ec.PrivateKey.from_wif(privkey_wif).sign(h).serialize() + bytes([SIGHASH.ALL])
    witness_script = script.Witness(
        items=[sig, bytes.fromhex(preimage_hex), bytes.fromhex(redeem_script_hex)]
    )

    psbt = Partial(tx=tx)
    psbt.inputs[0].witness_utxo = witness_utxo
    psbt.inputs[0].final_scriptwitness = witness_script
    if type(psbt) == PSET:
        rnd = os.urandom(32)
        psbt.blind(rnd)

    # finalize_psbt(psbt)

    # finalize
    ttx = Tx.parse(psbt.tx.serialize())
    ttx.vin[0].witness = witness_script

    if script_sig:
        ttx.vin[0].redeem_script = script_sig

    return bytes.hex(ttx.txid()), bytes.hex(ttx.serialize()), psbt.to_string()
