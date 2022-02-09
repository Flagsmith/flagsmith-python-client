class FlagsmithClientError(Exception):
    pass


class FlagsmithAPIError(FlagsmithClientError):
    pass


class FeatureDoesNotExist(FlagsmithClientError):
    pass
