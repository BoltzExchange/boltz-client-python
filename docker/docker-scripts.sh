#!/bin/sh
export COMPOSE_PROJECT_NAME=boltz-client

if [[ $(docker --help | grep compose) ]]; then
  # docker compose v2
  export COMPOSE_CMD="docker compose"
  export SEP="-"
else
  # docker compose v1
  export COMPOSE_CMD="docker-compose"
  export SEP="_"
fi

image-name() {
  echo "${COMPOSE_PROJECT_NAME}${SEP}$1${SEP}1"
}

bitcoin-cli-sim() {
  docker exec $(image-name bitcoind) bitcoin-cli -rpcuser=boltz -rpcpassword=boltz -regtest $@
}

lightning-cli-sim() {
  docker exec $(image-name corelightning) lightning-cli --network regtest $@
}

elements-cli-sim() {
  docker exec $(image-name elementsd) elements-cli "$@"
}

lncli-sim() {
  docker exec $(image-name lnd) lncli --network regtest --rpcserver=lnd:10009 $@
}

fund_corelightning_node() {
  address=$(lightning-cli-sim newaddr | jq -r .bech32)
  echo "funding: $address on corelightning node."
  bitcoin-cli-sim -named sendtoaddress address=$address amount=30 fee_rate=100 > /dev/null
}

fund_lnd_node() {
  address=$(lncli-sim newaddress p2wkh | jq -r .address)
  echo "funding: $address on lnd node."
  bitcoin-cli-sim -named sendtoaddress address=$address amount=30 fee_rate=100 > /dev/null
}

connect_corelightning_node() {
  pubkey=$(lightning-cli-sim getinfo | jq -r '.id')
  lightning-cli-sim connect $pubkey@$(image-name corelightning):9735 | jq -r '.id'
}

regtest-start(){
  regtest-stop
  $COMPOSE_CMD up -d --remove-orphans
  regtest-init
}

regtest-start-log(){
  regtest-stop
  $COMPOSE_CMD up --remove-orphans
  regtest-init
}

regtest-stop(){
  $COMPOSE_CMD down --volumes
  # clean up lightning node data
  sudo rm -rf ./data/corelightning ./data/lnd ./data/boltz/boltz.db ./data/elements/liquidregtest
  # recreate lightning node data folders preventing permission errors
  mkdir ./data/corelightning ./data/lnd
}

regtest-restart(){
  regtest-stop
  regtest-start
}

bitcoin-init(){
  echo "init_bitcoin_wallet..."
  bitcoin-cli-sim createwallet regtest || bitcoin-cli-sim loadwallet regtest
  echo "mining 150 blocks..."
  bitcoin-cli-sim -generate 150 > /dev/null
}

elements-init(){
  echo "init_elements_wallet..."
  docker logs regtest-elementsd-1
  sleep 10
  docker logs regtest-elementsd-1

  elements-cli-sim createwallet regtest || elements-cli-sim loadwallet regtest true
  echo "mining 150 liquid blocks..."
  elements-cli-sim -generate 150 > /dev/null
  elements-cli-sim rescanblockchain 0 > /dev/null
  echo "elements rescan blockchain..."
}

regtest-init(){
  bitcoin-init
  elements-init
  lightning-sync
  lightning-init
}

lightning-sync(){
  wait-for-corelightning-sync
  wait-for-lnd-sync
}

lightning-init(){

  # create 10 UTXOs for each node
  for i in 0 1 2 3 4; do
    fund_corelightning_node
    fund_lnd_node
  done

  echo "mining 10 blocks..."
  bitcoin-cli-sim -generate 10 > /dev/null

  echo "wait for 10s..."
  sleep 10 # else blockheight tests fail for cln

  lightning-sync

  channel_size=24000000 # 0.024 btc
  balance_size=12000000 # 0.12 btc
  balance_size_msat=12000000000 # 0.12 btc

  # lnd-1 -> cln-1
  lncli-sim connect $(lightning-cli-sim getinfo | jq -r '.id')@$(image-name corelightning) > /dev/null
  echo "open channel from lnd to corelightning"
  lncli-sim openchannel $(lightning-cli-sim getinfo | jq -r '.id') $channel_size $balance_size > /dev/null

  bitcoin-cli-sim -generate 10 > /dev/null
  wait-for-lnd-channel
  wait-for-corelightning-channel
  echo "wait for 15s... warmup..."
  sleep 15
  lightning-sync

}

wait-for-lnd-channel(){
  while true; do
    pending=$(lncli-sim pendingchannels | jq -r '.pending_open_channels | length')
    echo "lnd pendingchannels: $pending"
    if [[ "$pending" == "0" ]]; then
      break
    fi
    sleep 1
  done
}

wait-for-lnd-sync(){
  while true; do
    if [[ "$(lncli-sim getinfo 2>&1 | jq -r '.synced_to_chain' 2> /dev/null)" == "true" ]]; then
      echo "lnd is synced!"
      break
    fi
    echo "waiting for lnd to sync..."
    sleep 1
  done
}

wait-for-corelightning-channel(){
  while true; do
    pending=$(lightning-cli-sim getinfo | jq -r '.num_pending_channels | length')
    echo "corelightning pendingchannels: $pending"
    if [[ "$pending" == "0" ]]; then
      if [[ "$(lightning-cli-sim getinfo 2>&1 | jq -r '.warning_bitcoind_sync' 2> /dev/null)" == "null" ]]; then
        if [[ "$(lightning-cli-sim getinfo 2>&1 | jq -r '.warning_lightningd_sync' 2> /dev/null)" == "null" ]]; then
          break
        fi
      fi
    fi
    sleep 1
  done
}

wait-for-corelightning-sync(){
  while true; do
    if [[ ! "$(lightning-cli-sim getinfo 2>&1 | jq -r '.id' 2> /dev/null)" == "null" ]]; then
      if [[ "$(lightning-cli-sim getinfo 2>&1 | jq -r '.warning_bitcoind_sync' 2> /dev/null)" == "null" ]]; then
        if [[ "$(lightning-cli-sim getinfo 2>&1 | jq -r '.warning_lightningd_sync' 2> /dev/null)" == "null" ]]; then
          echo "corelightning is synced!"
          break
        fi
      fi
    fi
    echo "waiting for corelightning to sync..."
    sleep 1
  done
}
