"""
https://github.com/jgriffiths/wally_swap_test/blob/master/main.py
https://wally.readthedocs.io/en/release_0.8.9/psbt/
https://github.com/BlockchainCommons/Learning-Bitcoin-from-the-Command-Line/blob/master/07_1_Creating_a_Partially_Signed_Bitcoin_Transaction.md

"""
from __future__ import annotations
import json
import secrets
import wallycore as wally


FEE = 1000
LASSET = bytes.fromhex(
    "5ac9f65c0efcc4775e0baec4ec03abdde22473cd3cf33c0419ca290e0751b225"
)[::-1]


def set_blinding_data(idx, utxo, values, vbfs, assets, abfs):
    wally.map_add_integer(
        values, idx, wally.tx_confidential_value_from_satoshi(utxo["satoshi"])
    )
    wally.map_add_integer(vbfs, idx, utxo["amountblinder"])
    wally.map_add_integer(assets, idx, utxo["asset_id"])
    wally.map_add_integer(abfs, idx, utxo["assetblinder"])


def get_blinding_nonce(psbt, ephemeral_keys, output_index):
    ephemeral_key = wally.map_get_item(ephemeral_keys, 0)
    blinding_pubkey = wally.psbt_get_output_blinding_public_key(psbt, output_index)
    return wally.ecdh_nonce_hash(blinding_pubkey, ephemeral_key)


def get_entropy(num_outputs_to_blind):
    # For each output to blind, we need 32 bytes of entropy for each of:
    # - Output assetblinder
    # - Output amountblinder
    # - Ephemeral rangeproof ECDH key
    # - Explicit value rangeproof
    # - Surjectionproof seed
    return secrets.token_bytes(num_outputs_to_blind * 5 * 32)


# INIT
with open("./reverse_swap.json") as f:
    swap_json = f.read().strip()
with open("./lockup_rawtx.txt") as f:
    lockup_rawtx = f.read().strip()

reverse_swap = json.loads(swap_json)
redeem_script = bytes.fromhex(reverse_swap["redeem_script_hex"])
preimage = bytes.fromhex(reverse_swap["preimage_hex"])
private_key = wally.wif_to_bytes(
    reverse_swap["privkey_wif"],
    wally.WALLY_ADDRESS_VERSION_WIF_TESTNET,
    wally.WALLY_WIF_FLAG_COMPRESSED,
)
blinding_key = bytes.fromhex(reverse_swap["blinding_key"])

lockup_address = reverse_swap["lockup_address"]
lockup_blinding_pubkey = wally.confidential_addr_segwit_to_ec_public_key(
    lockup_address, "el"
)
lockup_unconfidential_address = wally.confidential_addr_to_addr_segwit(
    lockup_address, "el", "ert"
)
lockup_script_pubkey = wally.addr_segwit_to_bytes(
    lockup_unconfidential_address, "ert", 0
)

receive_address = reverse_swap["receive_address"]
receive_blinding_pubkey = wally.confidential_addr_segwit_to_ec_public_key(
    receive_address, "el"
)
receive_unconfidential_address = wally.confidential_addr_to_addr_segwit(
    receive_address, "el", "ert"
)
receive_script_pubkey = wally.addr_segwit_to_bytes(
    receive_unconfidential_address, "ert", 0
)


# parse lockup tx
lockup_tx = wally.tx_from_hex(hex=lockup_rawtx, flags=wally.WALLY_TX_FLAG_USE_ELEMENTS)
vout_n: int | None = None
for vout in range(wally.tx_get_num_outputs(lockup_tx)):
    script_out = wally.tx_get_output_script(lockup_tx, vout)
    if script_out == lockup_script_pubkey:
        vout_n = vout
        break

assert vout_n is not None, "Lockup vout not found"

txid = wally.tx_get_txid(lockup_tx)
lockup_script = wally.tx_get_output_script(lockup_tx, vout_n)
lockup_rangeproof = wally.tx_get_output_rangeproof(lockup_tx, vout_n)
lockup_ephemeral_pubkey = wally.tx_get_output_nonce(lockup_tx, vout_n)
lockup_asset_commitment = wally.tx_get_output_asset(lockup_tx, vout_n)
lockup_value_commitment = wally.tx_get_output_value(lockup_tx, vout_n)

# UNBLIND
unblinded_amount, unblinded_asset, vbf, abf = wally.asset_unblind(
    lockup_ephemeral_pubkey,
    blinding_key,
    lockup_rangeproof,
    lockup_value_commitment,
    lockup_script,
    lockup_asset_commitment,
)
utxo = {
    "satoshi": unblinded_amount,
    "amountblinder": abf,
    "asset_id": unblinded_asset,
    "assetblinder": vbf,
}

assert unblinded_asset == LASSET, "Wrong asset"


# PSBT
num_vin = 1
num_vout = 2
psbt = wally.psbt_init(
    wally.WALLY_PSBT_VERSION_2, num_vin, num_vout, 0, wally.WALLY_PSBT_INIT_PSET
)

# INPUT
idx = wally.psbt_get_num_inputs(psbt)
seq = 0xFFFFFFFE  # RBF not enabled for liquid yet
input = wally.tx_input_init(txid, vout_n, seq, None, None)
wally.psbt_add_tx_input_at(psbt, idx, 0, input)
wally.psbt_set_input_witness_utxo_from_tx(psbt, idx, lockup_tx, vout_n)
wally.psbt_set_input_utxo_rangeproof(psbt, idx, lockup_rangeproof)
wally.psbt_set_input_witness_script(psbt, idx, lockup_script)
wally.psbt_set_input_redeem_script(psbt, idx, redeem_script)
wally.psbt_set_input_amount_rangeproof(psbt, idx, lockup_rangeproof)

wally.psbt_generate_input_explicit_proofs(psbt, idx, utxo['satoshi'], utxo["asset_id"], utxo["assetblinder"], utxo["amountblinder"], secrets.token_bytes(32))



# OUTPUT
output_idx = wally.psbt_get_num_outputs(psbt)
asset_tag = bytearray([1]) + unblinded_asset

value = wally.tx_confidential_value_from_satoshi(unblinded_amount - FEE)
txout = wally.tx_elements_output_init(receive_script_pubkey, asset_tag, value, None)
wally.psbt_add_tx_output_at(psbt, output_idx, 0, txout)
wally.psbt_set_output_blinding_public_key(psbt, output_idx, receive_blinding_pubkey)
wally.psbt_set_output_blinder_index(psbt, output_idx, 0)

# Add the fee output
fee_value = wally.tx_confidential_value_from_satoshi(FEE)
fee_txout = wally.tx_elements_output_init(None, asset_tag, fee_value)
wally.psbt_add_tx_output_at(psbt, output_idx + 1, 0, fee_txout)


# BLINDING
entropy = get_entropy(1)
values, vbfs, assets, abfs = [wally.map_init(1, None) for _ in range(4)]
set_blinding_data(0, utxo, values, vbfs, assets, abfs)

ephemeral_keys = wally.psbt_blind(
    psbt, values, vbfs, assets, abfs, entropy, output_idx, 0
)
# nonce = get_blinding_nonce(psbt, ephemeral_keys, output_idx)



# signing
wally.psbt_sign(psbt, private_key, wally.EC_FLAG_ECDSA)

# Finalize
wally.psbt_finalize_input(psbt, idx, 0)
wally.psbt_finalize(psbt, 0)

tx = wally.psbt_extract(psbt, 1)

# signing
hash = wally.tx_get_elements_signature_hash(
    tx,
    0,
    lockup_script_pubkey,
    wally.tx_confidential_value_from_satoshi(unblinded_amount),
    wally.WALLY_SIGHASH_ALL,
    wally.WALLY_TX_FLAG_USE_WITNESS,
)
sig = wally.ec_sig_from_bytes(private_key, hash, wally.EC_FLAG_ECDSA)
witness_script = wally.tx_witness_stack_init(3)
wally.tx_witness_stack_add(witness_script, sig)
wally.tx_witness_stack_add(witness_script, preimage)
wally.tx_witness_stack_add(witness_script, redeem_script)
wally.tx_set_input_witness(tx, 0, witness_script)

tx_hex = wally.tx_to_hex(tx, wally.WALLY_TX_FLAG_USE_WITNESS)
#print(tx_hex)
print(wally.psbt_to_base64(psbt, wally.WALLY_PSBT_INIT_PSET))
