# Flagsmith Python SDK

> Flagsmith allows you to manage feature flags and remote config across multiple projects, environments and
> organisations.

The SDK for Python applications for [https://www.flagsmith.com/](https://www.flagsmith.com/).

## Adding to your project

For full documentation visit
[https://docs.flagsmith.com/clients/server-side?language=python](https://docs.flagsmith.com/clients/server-side?language=python).

### Sending events on shutdown

With `enable_events=True`, the client buffers events and sends them in the background. It does not send them when the
interpreter exits, so call `close()` when your application shuts down, or events still buffered are lost:

```python
import atexit

from flagsmith import Flagsmith

flagsmith = Flagsmith(environment_key="<your-environment-key>", enable_events=True)
atexit.register(flagsmith.close)
```

You can also call `flagsmith.close()` from your framework's shutdown hook. It waits up to 5 seconds by default; pass
`timeout_seconds` to change that.

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
