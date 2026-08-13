import itertools

class ProviderLoadBalancer:
    """Round-robin deployments within one provider only."""
    def __init__(self, deployments=("primary",)):
        self._cycle = itertools.cycle(deployments or ("primary",))

    def next(self) -> str:
        return next(self._cycle)
