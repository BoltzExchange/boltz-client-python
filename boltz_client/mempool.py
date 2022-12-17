import json
import logging
import httpx
import websockets

from typing import Optional

from binascii import hexlify
from embit.transaction import Transaction

from .helpers import req_wrap

logger = logging.getLogger()


class MempoolApiException(Exception):
    pass


class MempoolClient:
    def __init__(self, url):
        self._api_url = url

        # just check of mempool is available
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


    def get_fee_estimation(self) -> Optional[int]:
        # TODO: hardcoded maximum tx size, in the future we try to get the size of the tx via embit
        # we need a function like Transaction.vsize()
        tx_size_vbyte = 200
        mempool_fees = self.get_fees()
        if not mempool_fees:
            return None
        return mempool_fees * tx_size_vbyte


    def get_fees(self) -> Optional[int]:
        data = self.request(
            "get",
            f"{self._api_url}/api/v1/fees/recommended",
            headers={"Content-Type": "application/json"},
        )
        if not data:
            return None
        return int(data["economyFee"])


    def get_blockheight(self) -> int:
        data = self.request(
            "get",
            f"{self._api_url}/api/blocks/tip/height",
            headers={"Content-Type": "text/plain"},
        )
        return int(data["text"])


    def get_txs_from_address(self, address: str) -> dict:
        return self.request(
            "get",
            f"{self._api_url}/api/address/{address}/txs",
            headers={"Content-Type": "text/plain"},
        )


    def get_tx_from_address(self, address: str):
        data = self.get_txs_from_address(address)
        return self.get_tx_from_txs(data, address)


    def get_tx_from_txs(self, txs, address):
        if len(txs) == 0:
            return None
        for tx in txs:
            for i, vout in enumerate(tx["vout"]):
                if vout["scriptpubkey_address"] == address:
                    # tx = a_tx
                    # txid = a_tx["txid"]
                    # vout_cnt = i
                    # vout_amount = vout["value"]
                    return tx, vout


    def get_vout_from_tx(self, tx):
        if len(txs) == 0:
            return None
        for a_tx in txs:
            for i, vout in enumerate(a_tx["vout"]):
                if vout["scriptpubkey_address"] == address:
                    # tx = a_tx
                    # txid = a_tx["txid"]
                    # vout_cnt = i
                    # vout_amount = vout["value"]
                    return a_tx, vout


    def send_onchain_tx(self, tx: bytes):
        return self.request(
            "post",
            f"{self._api_url}/api/tx",
            headers={"Content-Type": "text/plain"},
            content=tx,
        )


    async def wait_for_websocket_message(self, send, message_string):
        async for websocket in websockets.connect(websocket_url):
            try:
                await websocket.send(json.dumps({"action": "want", "data": ["blocks"]}))
                await websocket.send(json.dumps(send))
                async for raw in websocket:
                    message = json.loads(raw)
                    if message_string in message:
                        return message.get(message_string)
            except websockets.ConnectionClosed:
                continue


    async def wait_for_onchain_tx(self, lockup_address, callback):
        task, txs = await callback()
        mempool_lockup_tx = self.get_tx_from_txs(txs, lockup_address)
        if mempool_lockup_tx:
            tx, txid, *_ = mempool_lockup_tx
            if swap.instant_settlement or tx["status"]["confirmed"]:
                logger.debug(
                    f"Boltz - reverse swap instant settlement, claiming immediatly..."
                )
                await self.create_claim_tx(swap, mempool_lockup_tx)
            else:
                await self.start_confirmation_listener(swap, mempool_lockup_tx)
            try:
                if task:
                    await task
            except:
                logger.error(
                    f"Boltz - could not await pay_invoice task, but sent onchain. should never happen!"
                )
        else:
            logger.error(f"Boltz - mempool lockup tx not found.")

# def start_onchain_listener(address) -> asyncio.Task:
#     return create_task_log_exception(
#         address, wait_for_onchain_tx(swap, swap_websocket_callback_restart)
#     )


# async def start_confirmation_listener(
#     swap: ReverseSubmarineSwap, mempool_lockup_tx
# ) -> asyncio.Task:
#     logger.debug(f"Boltz - reverse swap, waiting for confirmation...")

#     tx, txid, *_ = mempool_lockup_tx

#     confirmed = await wait_for_websocket_message({"track-tx": txid}, "txConfirmed")
#     if confirmed:
#         logger.debug(f"Boltz - reverse swap lockup transaction confirmed! claiming...")
#         await create_claim_tx(swap, mempool_lockup_tx)
#     else:
#         logger.debug(f"Boltz - reverse swap lockup transaction still not confirmed.")


# def create_task_log_exception(swap_id: str, awaitable: Awaitable) -> asyncio.Task:
#     async def _log_exception(awaitable):
#         try:
#             return await awaitable
#         except Exception as e:
#             logger.error(f"Boltz - reverse swap failed!: {swap_id} - {e}")
#             await update_swap_status(swap_id, "failed")
#     return asyncio.create_task(_log_exception(awaitable))


# async def swap_websocket_callback_initial(swap):
#     wstask = asyncio.create_task(
#         wait_for_websocket_message(
#             {"track-address": swap.lockup_address}, "address-transactions"
#         )
#     )
#     logger.debug(
#         f"Boltz - created task, waiting on mempool websocket for address: {swap.lockup_address}"
#     )

#     # create_task is used because pay_invoice is stuck as long as boltz does not
#     # see the onchain claim tx and it ends up in deadlock
#     task: asyncio.Task = create_task_log_exception(
#         swap.id,
#         pay_invoice(
#             wallet_id=swap.wallet,
#             payment_request=swap.invoice,
#             description=f"reverse swap for {swap.amount} sats on boltz.exchange",
#             extra={"tag": "boltz", "swap_id": swap.id, "reverse": True},
#         ),
#     )
#     logger.debug(f"Boltz - task pay_invoice created, reverse swap_id: {swap.id}")

#     done, pending = await asyncio.wait(
#         [task, wstask], return_when=asyncio.FIRST_COMPLETED
#     )
#     message = done.pop().result()

#     # pay_invoice already failed, do not wait for onchain tx anymore
#     if message is None:
#         logger.debug(f"Boltz - pay_invoice already failed cancel websocket task.")
#         wstask.cancel()
#         raise

#     return task, message


# async def swap_websocket_callback_restart(swap):
#     logger.debug(f"Boltz - swap_websocket_callback_restart called...")
#     message = await wait_for_websocket_message(
#         {"track-address": swap.lockup_address}, "address-transactions"
#     )
#     return None, message


# def check_block_height(block_height: int):
#     current_block_height = get_mempool_blockheight()
#     if current_block_height <= block_height:
#         msg = f"refund not possible, timeout_block_height ({block_height}) is not yet exceeded ({current_block_height})"
#         logger.debug(msg)
#         raise Exception(msg)


