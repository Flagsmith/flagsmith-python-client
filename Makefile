SDK_BENCHMARKS := tests/data/sdk-benchmarks

$(SDK_BENCHMARKS)/environments:
	git submodule update --init -- $(SDK_BENCHMARKS)

.PHONY: benchmark
benchmark: | $(SDK_BENCHMARKS)/environments
	poetry install --with dev,benchmark
	SDK_BENCHMARKS_ENVIRONMENTS_DIR=$(SDK_BENCHMARKS)/environments poetry run pytest benchmarks --codspeed
