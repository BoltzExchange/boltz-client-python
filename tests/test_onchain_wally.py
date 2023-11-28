import pytest
import wallycore as wally

from boltz_client.onchain_wally import NETWORKS, get_address_network, Network, is_possible_confidential_address, \
    decode_address


@pytest.mark.parametrize(
    "address, expected_network",
    [
        ("LQ1QQ2C8P2DV7CWH4PJW4YNL4UWLUCVXEAWYPPEYUPYYVFUUUTAAQSL87F966UEZGXKKGDFHZZWEPNDAWL2JZU3UC6HMAPNHY6XG4", NETWORKS[0]),

        ("lq1qq2c8p2dv7cwh4pjw4ynl4uwlucvxeawyppeyupyyvfuuutaaqsl87f966uezgxkkgdfhzzwepndawl2jzu3uc6hmapnhy6xg4", NETWORKS[0]),
        ("VJLApqRQPjHdBtTUQbWkePvmhU3p4SYfcRqX3BbxUpiKG3jfSW19oFULizTF7SPkcZp4uBf8TFMyu369", NETWORKS[0]),
        ("VTq4Wry5xzh7PzGsF3tqDDA3NveNzZjUEUZM4T5tUVgCBvnebMCiW8jYuZmb858dSU2bYVmZEZQu5jPG", NETWORKS[0]),

        ("tlq1qq2yycz9ms8y3nwj8jyxph3y0y7q54murxlf6jzc0ms35r0km09qcd6teckcu4pk2j07nsvyxk5rf030penz5svrj4zjcp3jcv", NETWORKS[1]),
        ("vjTudrrmqMSaEiMthDRwQbcPiGqUU7HwwVr243mgfeuRFJ8SoUkXDnTvHRtUPg3yaReoFSeHSyCq7XwW", NETWORKS[1]),
        ("vtSLD2eP5njy5Fkh7q58H9s2wGsRytGLLfWmzfnbRpVYvQDYhnxDEtdZZDBzuTkj72Fz16YXCQGSyFE8", NETWORKS[1]),

        ("el1qqgdry554u64x9uaj2egy9tlwqm68sqa024uvhmfn8kms8gzc6eg632lcuhh8fdq4adraffx6u9fjyz6zx8nas0txfae24mlzr", NETWORKS[2]),
        ("AzpmmwFSgXmWxhSAGtWyhfRiMTkBfy1dXJZvmaepbcCsc3RUmKxKT9uK9emXPMJnJQ67xJh3W4w8oTgb", NETWORKS[2]),
        ("CTEk5KDeMivFF9WqDCUcPNh94AcQfF6hpUYzprJmxCbXheeMxahgry5qcwVJ8k2mw1ECYs8KokTbj77R", NETWORKS[2]),
    ],
)
def test_get_address_network(address: str, expected_network: Network) -> None:
    assert get_address_network(wally, address) == expected_network


@pytest.mark.parametrize(
    "address, expected",
    [
        ("el1qqgdry554u64x9uaj2egy9tlwqm68sqa024uvhmfn8kms8gzc6eg632lcuhh8fdq4adraffx6u9fjyz6zx8nas0txfae24mlzr", False),
        ("AzpmmwFSgXmWxhSAGtWyhfRiMTkBfy1dXJZvmaepbcCsc3RUmKxKT9uK9emXPMJnJQ67xJh3W4w8oTgb", True),
        ("CTEk5KDeMivFF9WqDCUcPNh94AcQfF6hpUYzprJmxCbXheeMxahgry5qcwVJ8k2mw1ECYs8KokTbj77R", True),
    ],
)
def test_is_possible_confidential_address(address: str, expected: bool) -> None:
    assert is_possible_confidential_address(wally, address) == expected


@pytest.mark.parametrize(
    "address, blinding_pubkey, script_pubkey",
    [
        ("el1qqgdry554u64x9uaj2egy9tlwqm68sqa024uvhmfn8kms8gzc6eg632lcuhh8fdq4adraffx6u9fjyz6zx8nas0txfae24mlzr", "021a325295e6aa62f3b2565042afee06f47803af5578cbed333db703a058d651a8", "0014abf8e5ee74b415eb47d4a4dae153220b4231e7d8"),
        ("AzpmmwFSgXmWxhSAGtWyhfRiMTkBfy1dXJZvmaepbcCsc3RUmKxKT9uK9emXPMJnJQ67xJh3W4w8oTgb", "026792e6d7da21666c305fc7ab46fda31cf621b155914f5836a99b43ea5fca41d8", "a91423ec739a84326cc9a0dd1682457ad210d31bc43787"),
        ("CTEk5KDeMivFF9WqDCUcPNh94AcQfF6hpUYzprJmxCbXheeMxahgry5qcwVJ8k2mw1ECYs8KokTbj77R", "020e6c14fa10b893fb8c6fa2b378907e6e21d68c98591393f81b6078b636ba01d9", "76a91469c4e8147887c27542472b021cbd34458a714c5388ac"),
    ],
)
def test_decode_address(address: str, blinding_pubkey: str, script_pubkey: str) -> None:
    blinding, script = decode_address(wally, NETWORKS[2], address)
    assert blinding.hex() == blinding_pubkey
    assert script.hex() == script_pubkey
