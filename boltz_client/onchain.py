import os

from typing import Optional
from hashlib import sha256
from binascii import unhexlify, hexlify

from embit import ec, script
from embit.networks import NETWORKS
from embit.transaction import SIGHASH, Transaction, TransactionInput, TransactionOutput

from .mempool import LockupData


def create_preimage() -> tuple[str, str]:
    preimage = os.urandom(32)
    preimage_hash = sha256(preimage).hexdigest()
    return preimage.hex(), preimage_hash


def create_key_pair(network) -> tuple[str, str]:
    net = NETWORKS[network]
    privkey = ec.PrivateKey(os.urandom(32), True, net)
    pubkey_hex = hexlify(privkey.sec()).decode("UTF-8")
    privkey_wif = privkey.wif(net)
    return privkey_wif, pubkey_hex


def create_refund_tx(
    privkey_wif: str,
    receive_address: str,
    redeem_script_hex: str,
    timeout_block_height: int,
    lockup_tx: LockupData,
) -> tuple[str, str]:
    # encrypt redeemscript to script_sig
    rs = bytes([34]) + bytes([0]) + bytes([32])
    rs += sha256(unhexlify(redeem_script_hex)).digest()
    script_sig =  script.Script(data=rs)
    return create_onchain_tx(
        sequence=0xFFFFFFFE,
        redeem_script_hex=redeem_script_hex,
        privkey_wif=privkey_wif,
        lockup_tx=lockup_tx,
        receive_address=receive_address,
        timeout_block_height=timeout_block_height,
        script_sig=script_sig,
    )


def create_claim_tx(
    preimage_hex: str,
    privkey_wif: str,
    receive_address: str,
    redeem_script_hex: str,
    lockup_tx: LockupData
) -> tuple[str, str]:
    return create_onchain_tx(
        preimage_hex=preimage_hex,
        lockup_tx=lockup_tx,
        receive_address=receive_address,
        privkey_wif=privkey_wif,
        redeem_script_hex=redeem_script_hex,
    )


def create_onchain_tx(
    lockup_tx: LockupData,
    receive_address: str,
    privkey_wif: str,
    redeem_script_hex: str,
    fees: int = 1000,
    sequence: int = 0xFFFFFFFF,
    timeout_block_height: int = 0,
    preimage_hex: str = "",
    script_sig: Optional[script.Script]= None,
) -> tuple[str, str]:

    vin = TransactionInput(unhexlify(lockup_tx.txid), lockup_tx.vout_cnt, sequence=sequence)
    vout = TransactionOutput(lockup_tx.vout_amount - fees, script.address_to_scriptpubkey(receive_address))
    tx = Transaction(vin=[vin], vout=[vout])

    if timeout_block_height > 0:
        tx.locktime = timeout_block_height

    if script_sig:
        tx.vin[0].script_sig = script_sig

    # hashing redeemscript
    s = script.Script(data=unhexlify(redeem_script_hex))
    h = tx.sighash_segwit(0, s, lockup_tx.vout_amount)

    # sign the redeemscript hash
    privkey = ec.PrivateKey.from_wif(privkey_wif)
    sig = privkey.sign(h).serialize() + bytes([SIGHASH.ALL])

    # put the witness into the input
    witness_items = [sig, unhexlify(preimage_hex), unhexlify(redeem_script_hex)]
    tx.vin[0].witness = script.Witness(items=witness_items)

    return hexlify(tx.txid()).decode("UTF-8"), hexlify(tx.serialize()).decode("UTF-8")
