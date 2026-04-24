"""Microbenchmark for the Flagsmith Python SDK's local evaluation hot path.

Run with::

    poetry run python -m benchmarks.bench
    poetry run python -m benchmarks.bench --profile        # cProfile hot path
    poetry run python -m benchmarks.bench --iters 20000    # custom iter count

Mirrors the scenario from issue #198: enable_local_evaluation=True, a
single-identity call into get_identity_flags / get_environment_flags with
~262 features.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import statistics
import time
from typing import Callable, cast

from benchmarks.env import build_environment
from flagsmith import Flagsmith
from flagsmith.api.types import EnvironmentModel
from flagsmith.mappers import map_environment_document_to_context


def _make_client(n_features: int, with_multivariate: int = 0) -> Flagsmith:
    env_doc = cast(
        EnvironmentModel,
        build_environment(
            n_features=n_features,
            with_multivariate=with_multivariate,
        ),
    )
    # Build a local-eval client without hitting the network / starting polling.
    # The property setter on ``_evaluation_context`` initialises all the
    # derived caches we need; everything else below is what ``Flagsmith.__init__``
    # would otherwise set during its real construction path.
    client = Flagsmith.__new__(Flagsmith)
    client.offline_mode = False
    client.enable_local_evaluation = True
    client.offline_handler = None
    client.default_flag_handler = None
    client.enable_realtime_updates = False
    client._analytics_processor = None
    client._pipeline_analytics_processor = None
    client._environment_updated_at = None
    client._evaluation_context = map_environment_document_to_context(env_doc)
    return client


def _bench(
    name: str,
    fn: Callable[[], object],
    *,
    iters: int,
    warmup: int,
) -> None:
    for _ in range(warmup):
        fn()

    samples: list[float] = []
    # Break total iters into batches so we can also report a stdev.
    batch_size = max(1, iters // 20)
    for _ in range(0, iters, batch_size):
        n = min(batch_size, iters)
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        samples.append((time.perf_counter() - t0) / n)
        iters -= n

    p50 = statistics.median(samples) * 1e6
    mean = statistics.fmean(samples) * 1e6
    stdev = statistics.pstdev(samples) * 1e6
    print(
        f"{name:<32} p50={p50:8.2f} µs  mean={mean:8.2f} µs  stdev={stdev:7.2f} µs  "
        f"throughput={1e6 / mean:>10,.0f}/s"
    )


def run(iters: int, warmup: int, n_features: int, with_multivariate: int) -> None:
    client = _make_client(n_features, with_multivariate=with_multivariate)
    traits = {"venue_id": "12345"}

    print(
        f"Flagsmith local-eval benchmark | features={n_features} "
        f"multivariate={with_multivariate} iters={iters} warmup={warmup}"
    )
    _bench(
        "get_environment_flags",
        client.get_environment_flags,
        iters=iters,
        warmup=warmup,
    )
    _bench(
        "get_identity_flags",
        lambda: client.get_identity_flags(identifier="anonymous", traits=traits),
        iters=iters,
        warmup=warmup,
    )

    flags = client.get_identity_flags(identifier="anonymous", traits=traits)
    name = next(iter(flags.flags))
    _bench(
        "is_feature_enabled (cached)",
        lambda: flags.is_feature_enabled(name),
        iters=iters * 10,
        warmup=warmup,
    )


def profile(
    iters: int,
    n_features: int,
    output: str | None,
    with_multivariate: int = 0,
) -> None:
    client = _make_client(n_features, with_multivariate=with_multivariate)
    traits = {"venue_id": "12345"}

    # Warm up JSONPath caches, lru_cache, etc.
    for _ in range(200):
        client.get_identity_flags(identifier="anonymous", traits=traits)

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(iters):
        client.get_identity_flags(identifier="anonymous", traits=traits)
    profiler.disable()

    stats = pstats.Stats(profiler).sort_stats(pstats.SortKey.CUMULATIVE)
    stats.print_stats(30)
    stats.sort_stats(pstats.SortKey.TIME).print_stats(30)

    if output:
        profiler.dump_stats(output)
        print(f"wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iters", type=int, default=5000)
    parser.add_argument("--warmup", type=int, default=500)
    parser.add_argument("--features", type=int, default=262)
    parser.add_argument(
        "--multivariate",
        type=int,
        default=0,
        help="number of features that should have 2-way multivariate variants",
    )
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--profile-output", default=None)
    parser.add_argument("--json", action="store_true", help="emit JSON summary")
    args = parser.parse_args()

    if args.profile:
        profile(
            args.iters,
            args.features,
            args.profile_output,
            with_multivariate=args.multivariate,
        )
        return

    if args.json:
        # Alternative machine-readable mode for diffing runs.
        client = _make_client(args.features)
        traits = {"venue_id": "12345"}

        def _measure(fn: Callable[[], object], count: int) -> float:
            for _ in range(args.warmup):
                fn()
            t0 = time.perf_counter()
            for _ in range(count):
                fn()
            return (time.perf_counter() - t0) / count

        result = {
            "features": args.features,
            "iters": args.iters,
            "get_environment_flags_us": _measure(
                client.get_environment_flags, args.iters
            )
            * 1e6,
            "get_identity_flags_us": _measure(
                lambda: client.get_identity_flags(
                    identifier="anonymous", traits=traits
                ),
                args.iters,
            )
            * 1e6,
        }
        print(json.dumps(result, indent=2))
        return

    run(args.iters, args.warmup, args.features, args.multivariate)


if __name__ == "__main__":
    main()
