# Flagsmith Python SDK

> Flagsmith allows you to manage feature flags and remote config across multiple projects, environments and
> organisations.

The SDK for Python applications for [https://www.flagsmith.com/](https://www.flagsmith.com/).

## Adding to your project

For full documentation visit
[https://docs.flagsmith.com/clients/server-side?language=python](https://docs.flagsmith.com/clients/server-side?language=python).

## Checking client readiness

`flagsmith.ready()` returns whether the client has an environment document
available for local or offline evaluation. It makes no network requests and
does not block. Remote-evaluation clients return `True` immediately; readiness
does not indicate API connectivity or document freshness.

If the initial local-evaluation fetch fails and no document is available,
clients with realtime updates disabled are not ready until the background
poller loads a document. With realtime updates enabled, construction raises
`ValueError` instead. A later refresh failure keeps the last successful
document available, so readiness remains `True`.

Check readiness before evaluating flags to avoid the existing remote API
fallback while the first local document is unavailable:

```python
if flagsmith.ready():
    enabled = flagsmith.get_environment_flags().is_feature_enabled("feature")
else:
    enabled = False  # Application-defined fallback while waiting for a document.
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull
requests

## Getting Help

If you encounter a bug or feature request we would like to hear about it. Before you submit an issue please search
existing issues in order to prevent duplicates.

## Get in touch

If you have any questions about our projects you can email
<a href="mailto:support@flagsmith.com">support@flagsmith.com</a>.

## Useful links

[Website](https://www.flagsmith.com/)

[Documentation](https://docs.flagsmith.com/)
