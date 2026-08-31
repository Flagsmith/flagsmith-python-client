from importlib.metadata import version

__version__ = version("flagsmith")

DEFAULT_USER_AGENT = f"flagsmith-python-sdk/{__version__}"
