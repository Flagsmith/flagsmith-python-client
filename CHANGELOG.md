# Changelog

## [3.8.0](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.7.0...v3.8.0) (2024-08-12)


### Features

* Support transient identities and traits ([#93](https://github.com/Flagsmith/flagsmith-python-client/issues/93)) ([0a11db5](https://github.com/Flagsmith/flagsmith-python-client/commit/0a11db5a1010c177856716e6b90292651fa5889b))


### Bug Fixes

* Flaky `test_offline_mode__local_evaluation__correct_fallback` ([#103](https://github.com/Flagsmith/flagsmith-python-client/issues/103)) ([a2136d7](https://github.com/Flagsmith/flagsmith-python-client/commit/a2136d7cb73e819da8a7a08ab98a3c7bfaa52df9))
* Offline handler not used as fallback for local evaluation mode during init ([#100](https://github.com/Flagsmith/flagsmith-python-client/issues/100)) ([6f6d595](https://github.com/Flagsmith/flagsmith-python-client/commit/6f6d5950bc3a6befd953dc1a24ef497a4a018c7b))
* Package version not bumped during automatic release ([#102](https://github.com/Flagsmith/flagsmith-python-client/issues/102)) ([840bc0e](https://github.com/Flagsmith/flagsmith-python-client/commit/840bc0e33803a66af2342ec7ff0053744ada603d))

## [v3.7.0](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.7.0) - 17 Jul 2024

### What's Changed

- Bump black from 23.12.1 to 24.3.0 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/81
- chore: update github actions by [@dabeeeenster](https://github.com/dabeeeenster) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/82
- Remove pytz and replace usage with core python modules by [@MerijnBol](https://github.com/MerijnBol) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/80
- docs: misc README improvements by [@rolodato](https://github.com/rolodato) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/84
- Bump idna from 3.6 to 3.7 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/83
- Bump requests from 2.31.0 to 2.32.0 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/85
- Bump urllib3 from 2.2.1 to 2.2.2 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/87
- Bump certifi from 2024.2.2 to 2024.7.4 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/89
- Bump setuptools from 69.1.1 to 70.0.0 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/90
- fix: Add a custom exception for invalid features by [@tushar5526](https://github.com/tushar5526) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/86
- chore: Bump package, fix README by [@khvn26](https://github.com/khvn26) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/92

### New Contributors

- [@MerijnBol](https://github.com/MerijnBol) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/80
- [@rolodato](https://github.com/rolodato) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/84

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.6.0...v3.7.0

[Changes][v3.7.0]

<a name="v3.6.0"></a>

## [v3.6.0](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.6.0) - 14 Mar 2024

### What's Changed

- [##61](https://github.com/Flagsmith/flagsmith-python-client/issues/61) SSE streaming manager by
  [@bne](https://github.com/bne) in https://github.com/Flagsmith/flagsmith-python-client/pull/73
- chore: remove examples by [@dabeeeenster](https://github.com/dabeeeenster) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/75
- feat: Add identity overrides to local evaluation mode by [@khvn26](https://github.com/khvn26) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/72
- feat: strict typing by [@tushar5526](https://github.com/tushar5526) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/70 and
  https://github.com/Flagsmith/flagsmith-python-client/pull/71
- ci: run pytest on push to main by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/78
- fix: Set the environment for local evaluation mode on init by [@zachaysan](https://github.com/zachaysan) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/76
- chore: version bump to 3.6.0 by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/79

### New Contributors

- [@tushar5526](https://github.com/tushar5526) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/71
- [@bne](https://github.com/bne) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/73
- [@zachaysan](https://github.com/zachaysan) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/76

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.5.0...v3.6.0

[Changes][v3.6.0]

<a name="v3.5.0"></a>

## [Version 3.5.0 (v3.5.0)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.5.0) - 23 Nov 2023

### Compatibility Notes

Flagsmith Python SDK 3.5.0 brings the new version of Flagsmith engine that depends on Pydantic V2. If you're still using
Pydantic V1 in your project, consider doing one of the following:

- Change your `pydantic` imports to `pydantic.v1`.
- Use the [bump-pydantic](https://github.com/pydantic/bump-pydantic) tool to migrate your code semi-automatically.

Refer to the [Pydantic V2 migration guide](https://docs.pydantic.dev/latest/migration/) for more info.

### What's Changed

- Bump `flagsmith-flag-engine` to 5.0.0 by [@khvn26](https://github.com/khvn26) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/69
- Ensure polling thread is resilient to errors and exceptions by [@goncalossilva](https://github.com/goncalossilva) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/60
- Bump certifi from 2023.5.7 to 2023.7.22 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/56
- Bump urllib3 from 2.0.4 to 2.0.7 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/64

### New Contributors

- [@goncalossilva](https://github.com/goncalossilva) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/60

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.4.0...v3.5.0

[Changes][v3.5.0]

<a name="v3.4.0"></a>

## [Version 3.4.0 (v3.4.0)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.4.0) - 31 Jul 2023

### What's Changed

- Implementation of offline mode (single client class) by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/50

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.3.0...v3.4.0

[Changes][v3.4.0]

<a name="v3.3.0"></a>

## [Version 3.3.0 (v3.3.0)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.3.0) - 27 Jul 2023

### What's Changed

- Update flag-engine by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/49

### New Contributors

- [@khvn26](https://github.com/khvn26) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/52

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.2.2...v3.3.0

[Changes][v3.3.0]

<a name="v3.2.2"></a>

## [Version 3.2.2 (v3.2.2)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.2.2) - 07 Jul 2023

### What's Changed

- Use daemon argument to ensure that polling manager is killed by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/47

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.2.1...v3.2.2

[Changes][v3.2.2]

<a name="v3.2.1"></a>

## [Version 3.2.1 (v3.2.1)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.2.1) - 19 May 2023

### What's Changed

- Bump flask from 2.0.2 to 2.2.5 in /example by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/44
- Bump certifi from 2021.10.8 to 2022.12.7 by [@dependabot](https://github.com/dependabot) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/36
- improvement/general-housekeeping by [@dabeeeenster](https://github.com/dabeeeenster) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/43
- chore/bump-version by [@dabeeeenster](https://github.com/dabeeeenster) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/45

### New Contributors

- [@dependabot](https://github.com/dependabot) made their first contribution in
  https://github.com/Flagsmith/flagsmith-python-client/pull/44

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.2.0...v3.2.1

[Changes][v3.2.1]

<a name="v3.2.0"></a>

## [Version 3.2.0 (v3.2.0)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.2.0) - 13 Jan 2023

### What's Changed

- Add proxies option to Flagsmith by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/39
- Release 3.2.0 by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/38

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.1.0...v3.2.0

[Changes][v3.2.0]

<a name="v3.1.0"></a>

## [Version 3.1.0 (v3.1.0)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.1.0) - 01 Nov 2022

### What's Changed

- Upgrade engine (2.3.0) by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/34
- Release 3.1.0 by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/33

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.0.1...v3.1.0

[Changes][v3.1.0]

<a name="v3.0.1"></a>

## [Version 3.0.1 (v3.0.1)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.0.1) - 13 Jul 2022

### What's Changed

- Use feature name instead of feature id by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/29
- Release 3.0.1 by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/30

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.0.0...v3.0.1

[Changes][v3.0.1]

<a name="v3.0.0"></a>

## [Version 3.0.0 (v3.0.0)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.0.0) - 07 Jun 2022

### What's Changed

- Feature/rewrite for client side eval by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/17
- Refactor default flag logic by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/22
- Expose segments by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/24
- Prevent initialisation with local evaluation without server key by [@matthewelwell](https://github.com/matthewelwell)
  in https://github.com/Flagsmith/flagsmith-python-client/pull/25
- Update default url to point to edge by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/27
- Release 3.0.0 by [@matthewelwell](https://github.com/matthewelwell) in
  https://github.com/Flagsmith/flagsmith-python-client/pull/16

**Full Changelog**: https://github.com/Flagsmith/flagsmith-python-client/compare/v1.0.1...v3.0.0

[Changes][v3.0.0]

<a name="v3.0.0-alpha.2"></a>

## [Version 3.0.0 alpha 2 (v3.0.0-alpha.2)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.0.0-alpha.2) - 30 May 2022

[Changes][v3.0.0-alpha.2]

<a name="v3.0.0-alpha.1"></a>

## [Version 3.0.0 - Alpha 1 (v3.0.0-alpha.1)](https://github.com/Flagsmith/flagsmith-python-client/releases/tag/v3.0.0-alpha.1) - 17 May 2022

First alpha release of v3.0.0

[Changes][v3.0.0-alpha.1]

[v3.7.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.6.0...v3.7.0
[v3.6.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.5.0...v3.6.0
[v3.5.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.4.0...v3.5.0
[v3.4.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.3.0...v3.4.0
[v3.3.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.2.2...v3.3.0
[v3.2.2]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.2.1...v3.2.2
[v3.2.1]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.2.0...v3.2.1
[v3.2.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.1.0...v3.2.0
[v3.1.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.0.1...v3.1.0
[v3.0.1]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.0.0...v3.0.1
[v3.0.0]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.0.0-alpha.2...v3.0.0
[v3.0.0-alpha.2]: https://github.com/Flagsmith/flagsmith-python-client/compare/v3.0.0-alpha.1...v3.0.0-alpha.2
[v3.0.0-alpha.1]: https://github.com/Flagsmith/flagsmith-python-client/tree/v3.0.0-alpha.1

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.7.2 -->
