import os
import httpx
import logging as logger
logger.basicConfig(level=logger.DEBUG, format='%(asctime)s: %(levelname)s - %(message)s')

from dataclasses import dataclass

from .onchain import create_key_pair, create_preimage, create_onchain_tx
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
class BoltzSwapResponse:
    id: str
    bip21: str
    address: str
    redeemScript: str
    acceptZeroConf: bool
    expectedAmount: int
    timeoutBlockHeight: int


@dataclass
class BoltzReverseSwapResponse:
    id: str


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


    def claim_reverse_swap(self, lockup_tx_id: str, receive_address: str):
        lockup_tx = self.mempool.get_lockup_tx()
        tx = create_onchain_tx(address, lockup_tx, fees)
        self.mempool.send_onchain_tx(tx)


    def refund_swap(self, lockup_tx_id: str, receive_address: str):
        pass


    def create_swap(self, payment_request: str, amount: int = 0) -> tuple[str, BoltzSwapResponse]:
        self.check_limits(amount)
        refund_privkey_wif, refund_pubkey_hex = create_key_pair(self._cfg.network)
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
        return refund_privkey_wif, BoltzSwapResponse(**data)


    async def create_reverse_swap(self, amount: int = 0) -> tuple[str, BoltzReverseSwapResponse]:
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

        claim_privkey_wif, claim_pubkey_hex = create_key_pair(self._cfg.network)

        logger.info(f"claim_privkey_wif: {claim_privkey_wif}")

        preimage_hex, preimage_hash = create_preimage()
        logger.info(f"preimage hex: {preimage_hex}")

        data = self.request(
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

        swap = BoltzReverseSwapResponse(**data)

        logger.info(
            f"Boltz - created reverse swap, boltz_id: {swap.id}."
        )

#         task = create_task_log_exception(
#             swap.id, wait_for_onchain_tx(swap, swap_websocket_callback_initial)
#         )

        return claim_privkey_wif, swap
