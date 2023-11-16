#!/bin/bash

# elements-cli-sim createpsbt [{
#     "txid":"hex",
#     "vout":n,
#     "sequence":n,
#     "pegin_bitcoin_tx":"hex",
#     "pegin_txout_proof":"hex",
#     "pegin_claim_script":"hex",
#     "issuance_amount":n,
#     "issuance_tokens":n,
#     "asset_entropy":"hex",
#     "asset_blinding_nonce":"hex",
#     "blind_reissuance":bool
# }] [{
#     "address":amount,
#     "blinder_index":n,
#     "asset":"str"
# }] locktime replaceable psbt_version
CLI='docker exec boltz-client-elementsd-1 elements-cli'




address=$($CLI getnewaddress)
txid=$($CLI listunspent | jq -r .[0].txid)
vout=$($CLI listunspent | jq -r .[0].vout)
# txid=
# vout=1


psbt=$(poetry run python3 psbt.py)
$CLI decoderawtransaction $psbt | jq
$CLI sendrawtransaction $psbt
$CLI -generate 1
# $CLI decodepsbt $psbt
# $CLI analyzepsbt $psbt
exit 1
# psbt=$($CLI createpsbt \
#     "[{\"txid\":\"$txid\",\"vout\":$vout}]" \
#     "[{\"$address\":\"0.001\",\"blinder_index\":0}]")


# $CLI decodepsbt $psbt
# $CLI analyzepsbt $psbt


# echo $psbt
# exit 1

psbt=$($CLI walletcreatefundedpsbt \
    "[{\"txid\":\"$txid\",\"vout\":$vout}]" \
    "[{\"$address\":\"0.001\",\"blinder_index\":0}]" \
    | jq -r .psbt
)

echo $psbt


echo "UNBLINDED"
$CLI analyzepsbt $psbt | jq
$CLI decodepsbt $psbt | jq

exit 1
echo "BLINDED"
blinded=$($CLI walletprocesspsbt $psbt | jq -r .psbt)
$CLI analyzepsbt $blinded | jq

echo "FINALIZED"
rawtx=$($CLI finalizepsbt $blinded | jq -r .hex)
$CLI decoderawtransaction $rawtx | jq

echo "SENDRAWTRANSACTION"
$CLI sendrawtransaction $rawtx
$CLI -generate 1
