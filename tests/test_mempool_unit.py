import importlib
import sys
import types

import pytest


def _load_mempool_module(monkeypatch):
    fake_pymempool = types.ModuleType("pymempool")

    class StubMempoolAPI:
        def __init__(self, api_base_url):
            self.api_base_url = api_base_url
            self.n_fee_blocks = None
            self.calls = {
                "get_block_tip_hash": 0,
                "get_block": 0,
                "get_block_tip_height": 0,
                "get_recommended_fees": 0,
                "get_difficulty_adjustment": 0,
                "get_mempool_blocks_fee": 0,
                "get_block_height": 0,
            }

        def _track(self, name):
            self.calls[name] += 1

        def get_block_tip_hash(self):
            self._track("get_block_tip_hash")
            return "tip-hash"

        def get_block(self, block_hash):
            self._track("get_block")
            return {"hash": block_hash, "height": 840000, "timestamp": 1700000000}

        def get_block_tip_height(self):
            self._track("get_block_tip_height")
            return 840000

        def get_recommended_fees(self):
            self._track("get_recommended_fees")
            return {"fastestFee": 20, "halfHourFee": 12, "hourFee": 8}

        def get_difficulty_adjustment(self):
            self._track("get_difficulty_adjustment")
            return {"last_retarget": 838656, "minutes_between_blocks": 9.5}

        def get_mempool_blocks_fee(self):
            self._track("get_mempool_blocks_fee")
            return {
                "blocks": [1, 2, 3],
                "count": 321000,
                "vsize": 2300000,
                "minFee": [1, 2, 3, 4, 5, 6, 7],
                "medianFee": 4,
                "maxFee": 99,
            }

        def get_block_height(self, height):
            self._track("get_block_height")
            return f"height-hash-{height}"

    class StubRecommendedFees:
        def __init__(self, recommended_fees, mempool_blocks_fee):
            self.fastest_fee = recommended_fees["fastestFee"]
            self.half_hour_fee = recommended_fees["halfHourFee"]
            self.hour_fee = recommended_fees["hourFee"]
            self.mempool_tx_count = mempool_blocks_fee["count"]
            self.mempool_vsize = mempool_blocks_fee["vsize"]
            self.mempool_blocks = mempool_blocks_fee["blocks"]
            self._mempool_blocks_fee = mempool_blocks_fee

        def build_fee_array(self):
            return (
                self._mempool_blocks_fee["minFee"],
                self._mempool_blocks_fee["medianFee"],
                self._mempool_blocks_fee["maxFee"],
            )

    class StubDifficultyAdjustment:
        def __init__(self, lastblocknum, difficulty):
            self.last_retarget = difficulty["last_retarget"]
            self.minutes_between_blocks = difficulty["minutes_between_blocks"]

    fake_pymempool.MempoolAPI = StubMempoolAPI
    fake_pymempool.RecommendedFees = StubRecommendedFees
    fake_pymempool.DifficultyAdjustment = StubDifficultyAdjustment
    monkeypatch.setitem(sys.modules, "pymempool", fake_pymempool)

    sys.modules.pop("btcticker.mempool", None)
    return importlib.import_module("btcticker.mempool")


@pytest.fixture
def mempool_module(monkeypatch):
    return _load_mempool_module(monkeypatch)


def test_refresh_populates_expected_fields(mempool_module):
    mempool = mempool_module.Mempool(api_url="https://example/api", n_fee_blocks=5)

    data = mempool.getData()
    assert mempool.mempool.n_fee_blocks == 5
    assert data["tip_hash"] == "tip-hash"
    assert data["height"] == 840000
    assert data["bestFees"] == {"fastestFee": 20, "halfHourFee": 12, "hourFee": 8}
    assert data["count"] == 321000
    assert data["vsize"] == 2300000
    assert data["minFee"] == [1, 2, 3, 4, 5, 6, 7]
    assert data["medianFee"] == 4
    assert data["maxFee"] == 99
    assert data["last_retarget"] == 838656
    assert data["minutes_between_blocks"] == 9.5
    assert data["retarget_block"]["hash"] == "height-hash-838656"


def test_refresh_respects_min_refresh_time_cache(mempool_module, monkeypatch):
    timestamps = iter([100.0, 105.0, 120.0])
    monkeypatch.setattr(mempool_module.time, "time", lambda: next(timestamps))

    mempool = mempool_module.Mempool()
    first_call_count = mempool.mempool.calls["get_block_tip_hash"]

    mempool.refresh()
    assert mempool.mempool.calls["get_block_tip_hash"] == first_call_count

    mempool.refresh()
    assert mempool.mempool.calls["get_block_tip_hash"] == first_call_count + 1
