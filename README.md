# Flagsmith Python SDK

> Flagsmith allows you to manage feature flags and remote config across multiple projects, environments and
> organisations.

The SDK for Python applications for [https://www.flagsmith.com/](https://www.flagsmith.com/).

## Adding to your project

For full documentation visit
[https://docs.flagsmith.com/clients/server-side?language=python](https://docs.flagsmith.com/clients/server-side?language=python).

### Sending flag analytics to a different host than evaluations

When evaluating flags through an Edge Proxy (or another host that does not handle
the analytics endpoint), pass `analytics_url` to send flag analytics directly to the
core Flagsmith API while keeping flag evaluations on the proxy:

```python
from flagsmith import Flagsmith

flagsmith = Flagsmith(
    environment_key="<your API key>",
    api_url="https://edge-proxy.internal/api/v1/",
    analytics_url="https://edge.api.flagsmith.com/api/v1/analytics/flags/",
    enable_local_evaluation=True,
    enable_analytics=True,
)
```

When `analytics_url` is unset, analytics continue to post to
`<api_url>/analytics/flags/` as before.

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
