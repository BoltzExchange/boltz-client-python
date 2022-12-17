import os
import httpx
import logging as logger
logger.basicConfig(level=logger.DEBUG, format='%(asctime)s: %(levelname)s - %(message)s')

from dataclasses import dataclass
from binascii import hexlify
from hashlib import sha256
from typing import Optional

from embit import ec, script
from embit.networks import NETWORKS
# from embit.transaction import SIGHASH, Transaction, TransactionInput, TransactionOutput

from .helpers import req_wrap
from .mempool import MempoolClient



class BoltzLimitException(Exception):
    pass

class BoltzApiException(Exception):
    pass

class BoltzNotFoundException(Exception):
    pass


@dataclass
class BoltzSwapStatusResponse:
    status: str


@dataclass
class BoltzCreateSwapResponse:
    id: str
    bip21: str
    address: str
    redeemScript: str
    acceptZeroConf: bool
    expectedAmount: int
    timeoutBlockHeight: int


@dataclass
class BoltzConfig:
    network: str = "main"
    api_url: str = "https://boltz.exchange/api"
    mempool_url: str = "https://mempool.space"
    referral_id: str = "dni"


class BoltzClient:
    def __init__(self, config: BoltzConfig):
        logger.info(f"initialized boltz client: {config.api_url}")
        self._cfg = config
        self.log_config()

        self.net = NETWORKS[config.network]
        self.limit_minimal = 0
        self.limit_maximal = 0

        self.check_version()
        self.set_limits()
        self.mempool = MempoolClient(self._cfg.mempool_url)


    def log_config(self):
        for key in self._cfg.__dataclass_fields__:
            logger.debug(f"{key}: {getattr(self._cfg, key)}")


    def request(self, funcname, *args, **kwargs) -> dict:
        try:
            return req_wrap(funcname, *args, **kwargs)
        except httpx.RequestError as exc:
            msg = f"unreachable: {exc.request.url!r}."
            raise BoltzApiException(f"boltz api connection error: {msg}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise BoltzNotFoundException(exc.response.json()['error'])
            msg = f"{exc.response.status_code} while requesting {exc.request.url!r}. message: {exc.response.json()['error']}"
            raise BoltzApiException(f"boltz api status error: {msg}")


    def check_version(self):
        return self.request(
            "get",
            f"{self._cfg.api_url}/version",
            headers={"Content-Type": "application/json"},
        )


    def set_limits(self) -> None:
        data = self.request(
            "get",
            f"{self._cfg.api_url}/getpairs",
            headers={"Content-Type": "application/json"},
        )
        limits = data["pairs"]["BTC/BTC"]["limits"]
        self.limit_maximal = limits["maximal"]
        self.limit_minimal = limits["minimal"]


    def check_limits(self, amount: int) -> None:
        valid = amount >= self.limit_minimal and amount <= self.limit_maximal
        if not valid:
            msg = f"Boltz - swap not in boltz limits, amount: {amount}"
            raise BoltzLimitException(msg)


    def swap_status(self, boltz_id: str) -> BoltzSwapStatusResponse:
        data = self.request(
            "post",
            f"{self._cfg.api_url}/swapstatus",
            json={"id": boltz_id},
            headers={"Content-Type": "application/json"},
        )
        return BoltzSwapStatusResponse(**data)


    def create_key_pair(self) -> tuple[str, str]:
        privkey = ec.PrivateKey(os.urandom(32), True, self.net)
        pubkey_hex = hexlify(privkey.sec()).decode("UTF-8")
        privkey_wif = privkey.wif(self.net)
        return privkey_wif, pubkey_hex


    def create_swap(self, payment_request: str, amount: int = 0) -> tuple[str, BoltzCreateSwapResponse]:
        self.check_limits(amount)
        refund_privkey_wif, refund_pubkey_hex = self.create_key_pair()
        data = self.request(
            "post",
            f"{self._cfg.api_url}/createswap",
            json={
                "type": "submarine",
                "pairId": "BTC/BTC",
                "orderSide": "sell",
                "refundPublicKey": refund_pubkey_hex,
                "invoice": payment_request,
                "referralId": self._cfg.referral_id,
            },
            headers={"Content-Type": "application/json"},
        )
        return refund_privkey_wif, BoltzCreateSwapResponse(**data)


    async def create_reverse_swap(self, amount: int = 0) -> tuple[str, dict]:
        """
        explanation taken from electrum
        send on Lightning, receive on-chain
        - User generates preimage, RHASH. Sends RHASH to server.
        - Server creates an LN invoice for RHASH.
        - User pays LN invoice - except server needs to hold the HTLC as preimage is unknown.
        - Server creates on-chain output locked to RHASH.
        - User spends on-chain output, revealing preimage.
        - Server fulfills HTLC using preimage.
        Note: expected_onchain_amount_sat is BEFORE deducting the on-chain claim tx fee.
        """
        self.check_limits(amount)
        claim_privkey_wif, claim_pubkey_hex = self.create_key_pair()

        logger.info(f"claim_privkey_wif: {claim_privkey_wif}")

        preimage = os.urandom(32)
        preimage_hash = sha256(preimage).hexdigest()

        logger.info(f"preimage: {preimage.hex()}")

        res = req_wrap(
            "post",
            f"{self._cfg.api_url}/createswap",
            json={
                "type": "reversesubmarine",
                "pairId": "BTC/BTC",
                "orderSide": "buy",
                "invoiceAmount": amount,
                "preimageHash": preimage_hash,
                "claimPublicKey": claim_pubkey_hex,
                "referralId": self._cfg.referral_id,
            },
            headers={"Content-Type": "application/json"},
        )

        swap = res.json()

        logger.info(
            f"Boltz - created reverse swap, boltz_id: {res['id']}."
        )

#         task = create_task_log_exception(
#             swap.id, wait_for_onchain_tx(swap, swap_websocket_callback_initial)
#         )

        return claim_privkey_wif, swap


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


# async def create_claim_tx(swap: ReverseSubmarineSwap, mempool_lockup_tx):
#     tx = await create_onchain_tx(swap, mempool_lockup_tx)
#     await send_onchain_tx(tx)
#     logger.debug(f"Boltz - onchain tx sent, reverse swap completed")
#     await update_swap_status(swap.id, "complete")


# async def create_refund_tx(swap: SubmarineSwap):
#     mempool_lockup_tx = get_mempool_tx(swap.address)
#     tx = await create_onchain_tx(swap, mempool_lockup_tx)
#     await send_onchain_tx(tx)


# def check_block_height(block_height: int):
#     current_block_height = get_mempool_blockheight()
#     if current_block_height <= block_height:
#         msg = f"refund not possible, timeout_block_height ({block_height}) is not yet exceeded ({current_block_height})"
#         logger.debug(msg)
#         raise Exception(msg)


# """
# a submarine swap consists of 2 onchain tx's a lockup and a redeem tx.
# we create a tx to redeem the funds locked by the onchain lockup tx.
# claim tx for reverse swaps, refund tx for normal swaps they are the same
# onchain redeem tx, the difference between them is the private key, onchain_address,
# input sequence and input script_sig
# """


# async def create_onchain_tx(
#     swap: Union[ReverseSubmarineSwap, SubmarineSwap], mempool_lockup_tx
# ) -> Transaction:
#     is_refund_tx = type(swap) == SubmarineSwap
#     if is_refund_tx:
#         check_block_height(swap.timeout_block_height)
#         privkey = ec.PrivateKey.from_wif(swap.refund_privkey)
#         onchain_address = swap.refund_address
#         preimage = b""
#         sequence = 0xFFFFFFFE
#     else:
#         privkey = ec.PrivateKey.from_wif(swap.claim_privkey)
#         preimage = unhexlify(swap.preimage)
#         onchain_address = swap.onchain_address
#         sequence = 0xFFFFFFFF

#     locktime = swap.timeout_block_height
#     redeem_script = unhexlify(swap.redeem_script)

#     fees = get_fee_estimation()

#     tx, txid, vout_cnt, vout_amount = mempool_lockup_tx

#     script_pubkey = script.address_to_scriptpubkey(onchain_address)

#     vin = [TransactionInput(unhexlify(txid), vout_cnt, sequence=sequence)]
#     vout = [TransactionOutput(vout_amount - fees, script_pubkey)]
#     tx = Transaction(vin=vin, vout=vout)

#     if is_refund_tx:
#         tx.locktime = locktime

#     # TODO: 2 rounds for fee calculation, look at vbytes after signing and do another TX
#     s = script.Script(data=redeem_script)
#     for i, inp in enumerate(vin):
#         if is_refund_tx:
#             rs = bytes([34]) + bytes([0]) + bytes([32]) + sha256(redeem_script).digest()
#             tx.vin[i].script_sig = script.Script(data=rs)
#         h = tx.sighash_segwit(i, s, vout_amount)
#         sig = privkey.sign(h).serialize() + bytes([SIGHASH.ALL])
#         witness_items = [sig, preimage, redeem_script]
#         tx.vin[i].witness = script.Witness(items=witness_items)

#     return tx


# def get_swap_status(swap: Union[SubmarineSwap, ReverseSubmarineSwap]) -> SwapStatus:
#     swap_status = SwapStatus(
#         wallet=swap.wallet,
#         swap_id=swap.id,
#         status=swap.status,
#     )

#     try:
#         boltz_request = get_boltz_status(swap.boltz_id)
#         swap_status.boltz = boltz_request["status"]
#     except httpx.HTTPStatusError as exc:
#         json = exc.response.json()
#         swap_status.boltz = json["error"]
#         if "could not find" in swap_status.boltz:
#             swap_status.exists = False

#     if type(swap) == SubmarineSwap:
#         swap_status.reverse = False
#         swap_status.address = swap.address
#     else:
#         swap_status.reverse = True
#         swap_status.address = swap.lockup_address

#     swap_status.block_height = get_mempool_blockheight()
#     swap_status.timeout_block_height = (
#         f"{str(swap.timeout_block_height)} -> current: {str(swap_status.block_height)}"
#     )

#     if swap_status.block_height >= swap.timeout_block_height:
#         swap_status.hit_timeout = True

#     mempool_tx = get_mempool_tx(swap_status.address)
#     swap_status.lockup = mempool_tx
#     if mempool_tx == None:
#         swap_status.has_lockup = False
#         swap_status.confirmed = False
#         swap_status.mempool = "transaction.unknown"
#         swap_status.message = "lockup tx not in mempool"
#     else:
#         swap_status.has_lockup = True
#         tx, *_ = mempool_tx
#         if tx["status"]["confirmed"] == True:
#             swap_status.mempool = "transaction.confirmed"
#             swap_status.confirmed = True
#         else:
#             swap_status.confirmed = False
#             swap_status.mempool = "transaction.unconfirmed"

#     return swap_status
