"""Public entry points for ARTIQ master RPC."""

from sipyco import pc_rpc as rpc

from artiq_client.client_manager import get_manager


def get_artiq_rpc_client(target_name: str) -> rpc.Client:
    """Return a shared :class:`sipyco.pc_rpc.Client` for ``target_name``.

    Typical ``target_name`` values match ARTIQ master RPC targets, e.g.
    ``master_schedule``, ``master_experiment_db``, ``master_dataset_db``,
    ``master_device_db``.
    """
    return get_manager().get_client(target_name)
