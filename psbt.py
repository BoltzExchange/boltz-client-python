import os
import json
from embit.ec import PrivateKey
from embit.script import address_to_scriptpubkey, Script, Witness
from embit.liquid.addresses import addr_decode, to_unconfidential
from embit.liquid.pset import PSET
from embit.liquid.transaction import LTransaction, LTransactionOutput, LTransactionInput, TxInWitness, LSIGHASH

LASSET = bytes.fromhex("5ac9f65c0efcc4775e0baec4ec03abdde22473cd3cf33c0419ca290e0751b225")[::-1]

with open("./reverse_swap.json") as f:
    swap_json = f.read()

with open("./lockup_rawtx.txt") as f:
    lockup_rawtx = f.read()

reverse_swap = json.loads(swap_json)
# print(reverse_swap)

key = PrivateKey.from_wif(reverse_swap["privkey_wif"])
blinding_key = bytes.fromhex(reverse_swap["blinding_key"])
redeem_script = bytes.fromhex(reverse_swap["redeem_script_hex"])
preimage = bytes.fromhex(reverse_swap["preimage_hex"])

lockup_sc, lockup_pubkey = addr_decode(reverse_swap["lockup_address"])
receive_sc, receive_pubkey = addr_decode(reverse_swap["receive_address"])
assert lockup_pubkey, "Lockup pubkey not found"
assert receive_pubkey, "Receive pubkey not found"

lockup_tx: LTransaction = LTransaction.parse(bytes.fromhex(lockup_rawtx))

lockup_vout = None
lockup_vout_n: int | None = None
for i, lockup_vout in enumerate(lockup_tx.vout):
    if lockup_vout.script_pubkey == lockup_sc:
        lockup_vout = lockup_vout
        lockup_vout_n = i
        break

assert lockup_vout_n, "Lockup vout not found"
assert lockup_vout, "Lockup vout not found"

amount, asset, vbf, abf, extra, min_value, max_value = lockup_vout.unblind(blinding_key=blinding_key)

vin: LTransactionInput = LTransactionInput(vout=lockup_vout_n, txid=lockup_tx.txid())
vout: LTransactionOutput = LTransactionOutput(value=amount-1000, script_pubkey=receive_sc, asset=asset)
vout_fees: LTransactionOutput = LTransactionOutput(value=1000, script_pubkey=Script(), asset=asset)
tx: LTransaction = LTransaction( vin=[vin], vout=[vout, vout_fees])

hash = tx.sighash_segwit(0, Script(data=redeem_script), amount, LSIGHASH.ALL)
sig = key.sign(hash).serialize() + bytes([LSIGHASH.ALL])
witness_script = Witness( items=[ sig, preimage, redeem_script ])

tx.vin[0].witness = TxInWitness(script_witness=witness_script)
# print(tx)

psbt = PSET(tx=tx)
psbt.inputs[0].witness_utxo = lockup_vout
psbt.inputs[0].non_witness_utxo = lockup_tx
# psbt.s
# psbt.inputs[0].final_scriptwitness = witness_script
psbt.inputs[0].value = amount
psbt.inputs[0].asset = asset
psbt.outputs[0].blinding_pubkey = receive_pubkey.sec()
psbt.outputs[0].blinding_index = 0
psbt.unblind(blinding_key=blinding_key)
psbt.blind(os.urandom(32))
# psbt.inputs[0].value_blinding_factor = vbf
# psbt.inputs[0].asset_blinding_factor = abf
# psbt.inputs[0].min_value = min_value
# psbt.inputs[0].max_value = max_value
# psbt.outputs[0].blinding_index = 0  # type: ignore

psbt.verify()
# print(psbt.blinded_tx)


ttx = LTransaction.parse(psbt.blinded_tx.serialize())
hash = ttx.sighash_segwit(0, Script(data=redeem_script), amount, LSIGHASH.ALL)
sig = key.sign(hash).serialize() + bytes([LSIGHASH.ALL])
witness_script = Witness( items=[ sig, preimage, redeem_script ])
ttx.vin[0].witness = TxInWitness(script_witness=witness_script)
print(ttx)

# ttx.vin[0].witness = TxInWitness(script_witness=witness_script)
# print(ttx)

# # psbt.unblind(blinding_key=bytes.fromhex(blinding_key))

# hash = psbt.sighash_segwit(0, Script(data=bytes.fromhex(redeem_script)), amount)
# sig = key.sign(hash).serialize() + bytes([LSIGHASH.ALL])
# witness_script = Witness( items=[ sig, bytes.fromhex(preimage), bytes.fromhex(redeem_script) ])
# # print(witness_script)
# psbt.inputs[0].witness_script = witness_script

# seed = os.urandom(32)
# psbt.blind(seed)


# # psbt.sign_with(key)


# psbt.inputs[0].witness_utxo = witness_utxo
# psbt.inputs[0].non_witness_utxo = tx
# psbt.inputs[0].value = amount
# psbt.inputs[0].asset = asset
# psbt.inputs[0].value_blinding_factor = vbf
# psbt.inputs[0].asset_blinding_factor = abf
# psbt.inputs[0].min_value = min_value
# psbt.inputs[0].max_value = max_value
# print(psbt)

# psbt.outputs[0].blinding_pubkey = pubkey.sec()  # type: ignore
# psbt.outputs[0].blinding_index = 0  # type: ignore
# psbt.outputs[0].verify()
#         # psbt_tx = psbt.blinded_tx.serialize()
#         # # finalize
#         # ttx = LTransaction.parse(psbt_tx)
#         # ttx.vin[0].witness = witness_script

# psbt.unblind(blinding_key=bytes.fromhex(blinding_key))

# hash = psbt.sighash_segwit(0, Script(data=bytes.fromhex(redeem_script)), amount)
# sig = key.sign(hash).serialize() + bytes([LSIGHASH.ALL])
# witness_script = Witness( items=[ sig, bytes.fromhex(preimage), bytes.fromhex(redeem_script) ])

# psbt.inputs[0].redeem_script = Script(data=bytes.fromhex(redeem_script))
# psbt.inputs[0].final_scriptwitness = TxInWitness(script_witness=witness_script)
# psbt.sign_with(key)

# # psbt.verify()

# psbt.blind(os.urandom(32))

# print(psbt)

# print(psbt)
