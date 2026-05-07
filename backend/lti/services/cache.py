from pylti1p3.launch_data_storage.cache import CacheDataStorage


class FastAPICacheDataStorage(CacheDataStorage):
    _cache = None

    def __init__(self, cache, **kwargs):
        self._cache = cache
        super().__init__(cache, **kwargs)

    def get_launch_data(self, launch_id: str):
        return self.get_value(launch_id)

    def set_launch_data(self, launch_id: str, data, exp=None):
        return self.set_value(launch_id, data, exp=exp)