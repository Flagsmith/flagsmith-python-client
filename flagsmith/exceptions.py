class FlagsmithClientError(Exception):
    pass


class FlagsmithAPIError(FlagsmithClientError):
    pass


class FlagsmithFeatureDoesNotExistError(FlagsmithClientError):
    pass
