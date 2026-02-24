import logging
import time

from pymempool import DifficultyAdjustment, MempoolAPI, RecommendedFees

logger = logging.getLogger(__name__)


class Mempool:
    def __init__(
        self,
        api_url="https://mempool.space/api/,https://mempool.emzy.de/api/,"
        "https://mempool.bitcoin-21.org/api/",
        n_fee_blocks=7,
    ):
        self.mempoolApiUrl = api_url
        self.mempool = MempoolAPI(api_base_url=api_url)
        self.min_refresh_time = 10
        self.mempool.n_fee_blocks = n_fee_blocks
        self.data = {}
        self.refresh()

    def _is_cache_fresh(self, current_time):
        return (
            "timestamp" in self.data
            and current_time - self.data["timestamp"] < self.min_refresh_time
        )

    def _fetch_data(self, current_time):
        data = {"timestamp": current_time}
        bestFees = {"fastestFee": -1, "halfHourFee": -1, "hourFee": -1}

        logger.info("Getting Data")

        lastblockhash = self.mempool.get_block_tip_hash()
        rawblock = self.mempool.get_block(lastblockhash)

        lastblocknum = self.mempool.get_block_tip_height()
        recommended_fees = self.mempool.get_recommended_fees()
        difficulty = self.mempool.get_difficulty_adjustment()
        mempool_blocks_fee = self.mempool.get_mempool_blocks_fee()

        rf = RecommendedFees(recommended_fees, mempool_blocks_fee)
        da = DifficultyAdjustment(lastblocknum, difficulty)

        retarget_hash = self.mempool.get_block_height(da.last_retarget)
        raw_retarget_block = self.mempool.get_block(retarget_hash)

        bestFees["fastestFee"] = rf.fastest_fee
        bestFees["halfHourFee"] = rf.half_hour_fee
        bestFees["hourFee"] = rf.hour_fee

        minFee, medianFee, maxFee = rf.build_fee_array()
        data["count"] = rf.mempool_tx_count
        data["vsize"] = rf.mempool_vsize
        data["minFee"] = minFee
        data["maxFee"] = maxFee
        data["bestFees"] = bestFees
        data["medianFee"] = medianFee
        data["blocks"] = rf.mempool_blocks

        data["last_block"] = rawblock
        data["retarget_block"] = raw_retarget_block
        data["last_retarget"] = da.last_retarget
        data["minutes_between_blocks"] = da.minutes_between_blocks
        data["height"] = lastblocknum
        data["tip_hash"] = lastblockhash
        return data

    def refresh(self):
        current_time = time.time()
        if self._is_cache_fresh(current_time):
            return
        self.data = self._fetch_data(current_time)

    def getData(self):
        return self.data
