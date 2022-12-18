import json
import httpx
import websockets
import logging

from typing import Optional
from dataclasses import dataclass

from .helpers import req_wrap


@dataclass
class LockupData:
    status: str
    txid: str
    vout_cnt: int
    vout_amount: int


class MempoolApiException(Exception):
    pass


class MempoolBlockHeightException(Exception):
    pass


class MempoolClient:
    def __init__(self, url, ws_url):
        self._api_url = url
        self._ws_url = ws_url
        # just check if mempool is available
        self.get_blockheight()


    def request(self, funcname, *args, **kwargs) -> dict:
        try:
            return req_wrap(funcname, *args, **kwargs)
        except httpx.RequestError as exc:
            msg = f"unreachable: {exc.request.url!r}."
            raise MempoolApiException(f"mempool api connection error: {msg}")
        except httpx.HTTPStatusError as exc:
            msg = f"{exc.response.status_code} while requesting {exc.request.url!r}. message: {exc.response.text}"
            raise MempoolApiException(f"mempool api status error: {msg}")


    async def wait_for_websocket_message(self, send, message_string):
        async for websocket in websockets.connect(self._ws_url):
            try:
                await websocket.send(json.dumps({"action": "want", "data": ["blocks"]}))
                await websocket.send(json.dumps(send))
                async for raw in websocket:
                    # logging.error(raw)
                    message = json.loads(raw)
                    if message_string in message:
                        return message.get(message_string)
            except websockets.ConnectionClosed:
                websocket.close()


    async def wait_for_tx_confirmed(self, txid: str):
        return await self.wait_for_websocket_message({"track-tx": txid }, "txConfirmed")


    async def wait_for_address_transactions(self, address: str):
        return await self.wait_for_websocket_message({"track-address": address }, "address-transactions")


    def get_fee_estimation(self) -> int:
        # TODO: hardcoded maximum tx size, in the future we try to get the size of the tx via embit
        # we need a function like Transaction.vsize()
        tx_size_vbyte = 200
        mempool_fees = self.get_fees()
        return mempool_fees * tx_size_vbyte


    def get_fees(self) -> int:
        data = self.request(
            "get",
            f"{self._api_url}/api/v1/fees/recommended",
            headers={"Content-Type": "application/json"},
        )
        return int(data["economyFee"])


    def get_blockheight(self) -> int:
        data = self.request(
            "get",
            f"{self._api_url}/api/blocks/tip/height",
            headers={"Content-Type": "text/plain"},
        )
        return int(data["text"])


    def check_block_height(self, timeout_block_height: int) -> None:
        current_block_height = self.get_blockheight()
        if current_block_height < timeout_block_height:
            msg = f"current_block_height ({current_block_height}) has not yet exceeded ({timeout_block_height})"
            raise MempoolBlockHeightException(msg)


    def get_tx_from_address(self, address: str) -> Optional[LockupData]:
        txs = self.request(
            "get",
            f"{self._api_url}/api/address/{address}/txs",
            headers={"Content-Type": "application/json"},
        )
        if len(txs) == 0:
            return None

        for tx in txs:
            for i, vout in enumerate(tx["vout"]):
                if vout["scriptpubkey_address"] == address:
                    return LockupData(txid=tx["txid"], vout_cnt=i, vout_amount=vout["value"], status="test")
        return None


    def send_onchain_tx(self, tx_hex: str):
        return self.request(
            "post",
            f"{self._api_url}/api/tx",
            headers={"Content-Type": "text/plain"},
            content=tx_hex,
        )
