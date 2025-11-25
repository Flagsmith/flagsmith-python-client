# Changelog

## [5.0.3](https://github.com/Flagsmith/flagsmith-python-client/compare/v5.0.2...v5.0.3) (2025-11-25)


### Bug Fixes

* `get_environment_flags` includes segments in evaluation context ([#179](https://github.com/Flagsmith/flagsmith-python-client/issues/179)) ([470c4e3](https://github.com/Flagsmith/flagsmith-python-client/commit/470c4e3e71be55795387ab023b4fe6f7623d6aec))


### Dependency Updates

* Bump `flagsmith-flag-engine` to 10.0.3 ([#182](https://github.com/Flagsmith/flagsmith-python-client/issues/182)) ([cf54be5](https://github.com/Flagsmith/flagsmith-python-client/commit/cf54be555b3d3178cd1494e8fc775b0283ad1ee9))


### Other

* Standardize engine metadata ([#177](https://github.com/Flagsmith/flagsmith-python-client/issues/177)) ([c0d57ec](https://github.com/Flagsmith/flagsmith-python-client/commit/c0d57ec4cd208b79908298e6cf9a3504e5d42fda))

## [5.0.2](https://github.com/Flagsmith/flagsmith-python-client/compare/v5.0.1...v5.0.2) (2025-10-30)

### Dependency Updates

- Bump `flagsmith-flag-engine` to 10.0.2 ([#173](https://github.com/Flagsmith/flagsmith-python-client/issues/173))
  ([9a0fc58](https://github.com/Flagsmith/flagsmith-python-client/commit/9a0fc58dc4e7eb590271a76e62a29078cf54b01b))

## [5.0.1](https://github.com/Flagsmith/flagsmith-python-client/compare/v5.0.0...v5.0.1) (2025-10-28)

### Bug Fixes

- TypeError: 'NoneType' object is not subscriptable (Python 3.11)
  ([#170](https://github.com/Flagsmith/flagsmith-python-client/issues/170))
  ([c20f543](https://github.com/Flagsmith/flagsmith-python-client/commit/c20f54385390677657edcafc8c38204c5197e736))
- ValueError: Invalid isoformat string on Python 3.10
  ([#168](https://github.com/Flagsmith/flagsmith-python-client/issues/168))
  ([29dee4d](https://github.com/Flagsmith/flagsmith-python-client/commit/29dee4de219754ec9874e2db39287f065b2dc166))

### Dependency Updates

- Bump `flagsmith-flag-engine` to 10.0.1 ([#171](https://github.com/Flagsmith/flagsmith-python-client/issues/171))
  ([ab093bd](https://github.com/Flagsmith/flagsmith-python-client/commit/ab093bd71bf870461a153864eb2b9ea08533f852))

## [5.0.0](https://github.com/Flagsmith/flagsmith-python-client/compare/v4.0.1...v5.0.0) (2025-10-24)

### ⚠ BREAKING CHANGES

- Restore v3 `OfflineHandler` interface ([#162](https://github.com/Flagsmith/flagsmith-python-client/issues/162))

### Features

- Restore v3 `OfflineHandler` interface ([#162](https://github.com/Flagsmith/flagsmith-python-client/issues/162))
  ([374e292](https://github.com/Flagsmith/flagsmith-python-client/commit/374e29293aca44eafadda672907d9b701b8414fc))
- Support feature metadata ([#163](https://github.com/Flagsmith/flagsmith-python-client/issues/163))
  ([1bbbdf8](https://github.com/Flagsmith/flagsmith-python-client/commit/1bbbdf8d98054ea4317a1ba3bd95f437a7edbf0e))
- Support variant priority ([#161](https://github.com/Flagsmith/flagsmith-python-client/issues/161))
  ([4f84044](https://github.com/Flagsmith/flagsmith-python-client/commit/4f84044ea87a9d284f6731ff4cfe4835d5f99fa4))

### Bug Fixes

- `get_identity_segments` tries to return identity override segments
  ([#159](https://github.com/Flagsmith/flagsmith-python-client/issues/159))
  ([68d44a1](https://github.com/Flagsmith/flagsmith-python-client/commit/68d44a15feae75905d08103ff8dba53c605377fd))

### CI

- pre-commit autoupdate ([#158](https://github.com/Flagsmith/flagsmith-python-client/issues/158))
  ([e2fe6eb](https://github.com/Flagsmith/flagsmith-python-client/commit/e2fe6eb01ba61a2477d54e75abc636c00c7f1e10))

### Dependency Updates

- Bump `flagsmith-flag-engine` to 10.0.0 ([#165](https://github.com/Flagsmith/flagsmith-python-client/issues/165))
  ([68c40b5](https://github.com/Flagsmith/flagsmith-python-client/commit/68c40b554d4cbc9d7e3b5e31f7238de253648db1))
- bump urllib3 from 2.2.3 to 2.5.0 ([#157](https://github.com/Flagsmith/flagsmith-python-client/issues/157))
  ([5de9650](https://github.com/Flagsmith/flagsmith-python-client/commit/5de965027d94cd4cd62178615c7e6d14c5340b70))

## [4.0.1](https://github.com/Flagsmith/flagsmith-python-client/compare/v4.0.0...v4.0.1) (2025-09-19)

### Bug Fixes

- Environment name not mapped to evaluation context
  ([#153](https://github.com/Flagsmith/flagsmith-python-client/issues/153))
  ([3fcae7c](https://github.com/Flagsmith/flagsmith-python-client/commit/3fcae7c13fb36428ad8137195916f102e39e9453))
- Feature state `django_id` fields are not handled
  ([#156](https://github.com/Flagsmith/flagsmith-python-client/issues/156))
  ([860b630](https://github.com/Flagsmith/flagsmith-python-client/commit/860b6303cb310166d4bc740fcd8213f4c92164dd))

## [4.0.0](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.10.1...v4.0.0) (2025-09-02)

### ⚠ BREAKING CHANGES

- Engine V7 compatibility ([#150](https://github.com/Flagsmith/flagsmith-python-client/issues/150))

### Features

- Engine V7 compatibility ([#150](https://github.com/Flagsmith/flagsmith-python-client/issues/150))
  ([5ecb078](https://github.com/Flagsmith/flagsmith-python-client/commit/5ecb0788b6c2903826210e0c453d68769220d250))
- Standardised `User-Agent` ([#152](https://github.com/Flagsmith/flagsmith-python-client/issues/152))
  ([a0e96c9](https://github.com/Flagsmith/flagsmith-python-client/commit/a0e96c907f3401eb9fd801af05400e4ce92f8feb))

### Other

- Add `CODEOWNERS` ([#148](https://github.com/Flagsmith/flagsmith-python-client/issues/148))
  ([a55a921](https://github.com/Flagsmith/flagsmith-python-client/commit/a55a92136699af06390a6570850d45464dcad7aa))

## [3.10.1](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.10.0...v3.10.1) (2025-08-21)

### CI

- pre-commit autoupdate ([#137](https://github.com/Flagsmith/flagsmith-python-client/issues/137))
  ([0372818](https://github.com/Flagsmith/flagsmith-python-client/commit/0372818c9717021c583b561816f54d62eb8be88e))

### Other

- replacing-deprecated-methods ([#143](https://github.com/Flagsmith/flagsmith-python-client/issues/143))
  ([03715ab](https://github.com/Flagsmith/flagsmith-python-client/commit/03715abc403eeface2bd4d3d472b6da97d7d0e77))

## [3.10.0](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.9.2...v3.10.0) (2025-08-06)

### Features

- Support SDK metrics ([#136](https://github.com/Flagsmith/flagsmith-python-client/issues/136))
  ([441c46a](https://github.com/Flagsmith/flagsmith-python-client/commit/441c46a0ae72f1ecb8d6e0b4b82f24706c34f942))

### Other

- bump-flagsmith-engine-version ([#139](https://github.com/Flagsmith/flagsmith-python-client/issues/139))
  ([2cd2435](https://github.com/Flagsmith/flagsmith-python-client/commit/2cd2435d4f3872ea399ebeacadaee8c943707a1a))

## [3.9.2](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.9.1...v3.9.2) (2025-07-08)

### CI

- pre-commit autoupdate ([#128](https://github.com/Flagsmith/flagsmith-python-client/issues/128))
  ([62c55a9](https://github.com/Flagsmith/flagsmith-python-client/commit/62c55a996c5b3929ff1a710b95d1289482d85cd3))

### Docs

- removing hero image from SDK readme ([#131](https://github.com/Flagsmith/flagsmith-python-client/issues/131))
  ([80af1d8](https://github.com/Flagsmith/flagsmith-python-client/commit/80af1d8d4cc848029963d1f5fc55fe1e0feced0e))

### Other

- **actions:** Move project id to a var ([#126](https://github.com/Flagsmith/flagsmith-python-client/issues/126))
  ([3bd7943](https://github.com/Flagsmith/flagsmith-python-client/commit/3bd7943439e880b270d7c1303f1606c9504cf402))
- Add workflow to add new issues to engineering project
  ([#124](https://github.com/Flagsmith/flagsmith-python-client/issues/124))
  ([b67f9a6](https://github.com/Flagsmith/flagsmith-python-client/commit/b67f9a6c13467c12b476093362a8606b978f7456))
- **ci:** show all sections in release please config
  ([#132](https://github.com/Flagsmith/flagsmith-python-client/issues/132))
  ([e684919](https://github.com/Flagsmith/flagsmith-python-client/commit/e684919ba7a8ab93de0fc8b7214d1e8abe664157))
- **deps:** bump requests from 2.32.3 to 2.32.4
  ([#129](https://github.com/Flagsmith/flagsmith-python-client/issues/129))
  ([3019636](https://github.com/Flagsmith/flagsmith-python-client/commit/30196369bcfb55647f1456daee9e4f6da49963a7))
- **deps:** update flagsmith-flag-engine ([#133](https://github.com/Flagsmith/flagsmith-python-client/issues/133))
  ([bfcd454](https://github.com/Flagsmith/flagsmith-python-client/commit/bfcd454851a2b7b772e7937b94ccf4b1cdaba401))

## [3.9.1](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.9.0...v3.9.1) (2025-04-29)

### Bug Fixes

- Fix HTTP requests not timing out
  ([7d61a47](https://github.com/Flagsmith/flagsmith-python-client/commit/7d61a47d0e7ec500b77bec15403f655a159e01fa))

## [3.9.0](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.8.0...v3.9.0) (2025-04-01)

### Features

- Add utility functions for webhooks
  ([3d8df11](https://github.com/Flagsmith/flagsmith-python-client/commit/3d8df11ddf4656c5f20c0f558e1d7a3af412b960))

## [3.8.0](https://github.com/Flagsmith/flagsmith-python-client/compare/v3.7.0...v3.8.0) (2024-08-12)

### Features

- Support transient identities and traits ([#93](https://github.com/Flagsmith/flagsmith-python-client/issues/93))
  ([0a11db5](https://github.com/Flagsmith/flagsmith-python-client/commit/0a11db5a1010c177856716e6b90292651fa5889b))

### Bug Fixes

- Flaky `test_offline_mode__local_evaluation__correct_fallback`
  ([#103](https://github.com/Flagsmith/flagsmith-python-client/issues/103))
  ([a2136d7](https://github.com/Flagsmith/flagsmith-python-client/commit/a2136d7cb73e819da8a7a08ab98a3c7bfaa52df9))
- Offline handler not used as fallback for local evaluation mode during init
  ([#100](https://github.com/Flagsmith/flagsmith-python-client/issues/100))
  ([6f6d595](https://github.com/Flagsmith/flagsmith-python-client/commit/6f6d5950bc3a6befd953dc1a24ef497a4a018c7b))
- Package version not bumped during automatic release
  ([#102](https://github.com/Flagsmith/flagsmith-python-client/issues/102))
  ([840bc0e](https://github.com/Flagsmith/flagsmith-python-client/commit/840bc0e33803a66af2342ec7ff0053744ada603d))

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
