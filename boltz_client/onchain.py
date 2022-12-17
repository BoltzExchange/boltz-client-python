import os

from dataclasses import dataclass
from hashlib import sha256
from binascii import unhexlify, hexlify

from embit import ec, script
from embit.networks import NETWORKS
from embit.transaction import SIGHASH, Transaction, TransactionInput, TransactionOutput


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


@dataclass
class LockupData:
    txid: str
    vout_cnt: int
    vout_amount: int


def create_onchain_tx(
    lockup_tx: LockupData,
    receive_address: str,
    privkey_wif: str,
    redeem_script_hex: str,
    fees: int = 1000,
    timeout_block_height: int = 0,
    preimage_hex: str = "",
    refund: bool = False,
) -> Transaction:

    sequence = 0xFFFFFFFE if refund else 0xFFFFFFFF

    vin = TransactionInput(unhexlify(lockup_tx.txid), lockup_tx.vout_cnt, sequence=sequence)
    vout = TransactionOutput(lockup_tx.vout_amount - fees, script.address_to_scriptpubkey(receive_address))

    tx = Transaction(vin=[vin], vout=[vout])

    if refund:
        tx.locktime = timeout_block_height
        # encrypt redeemscript
        rs = bytes([34]) + bytes([0]) + bytes([32]) + sha256(unhexlify(redeem_script_hex)).digest()
        tx.vin[0].script_sig = script.Script(data=rs)

    # hashing redeemscript
    s = script.Script(data=unhexlify(redeem_script_hex))
    h = tx.sighash_segwit(0, s, lockup_tx.vout_amount)

    # sign the redeemscript hash
    privkey = ec.PrivateKey.from_wif(privkey_wif)
    sig = privkey.sign(h).serialize() + bytes([SIGHASH.ALL])

    # put the witness into the input
    witness_items = [sig, unhexlify(preimage_hex), unhexlify(redeem_script_hex)]
    tx.vin[0].witness = script.Witness(items=witness_items)

    return tx
