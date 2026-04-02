"""Thread-safe cache of sipyco RPC clients to the ARTIQ master."""

from __future__ import annotations

import threading

from django.conf import settings
from sipyco import pc_rpc as rpc

_manager: ArtiqRpcClientManager | None = None
_manager_lock = threading.Lock()


class ArtiqRpcClientManager:
    """Creates and reuses :class:`sipyco.pc_rpc.Client` per ``target_name``.

    WSGI may serve requests on multiple threads; all cache access is guarded by a lock.
    If concurrent RPC calls on one connection are unsafe for your workload, serialize
    those calls at a higher layer or use a process/thread model with one client each.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._clients: dict[str, rpc.Client] = {}
        self._lock = threading.Lock()

    def get_client(self, target_name: str) -> rpc.Client:
        with self._lock:
            if target_name not in self._clients:
                self._clients[target_name] = rpc.Client(
                    self._host, self._port, target_name
                )
            return self._clients[target_name]

    def reset_client(self, target_name: str) -> None:
        """Drop a cached client so the next ``get_client`` creates a new one."""
        with self._lock:
            self._clients.pop(target_name, None)

    def close_all(self) -> None:
        """Remove all cached clients (does not call sipyco close hooks if any)."""
        with self._lock:
            self._clients.clear()


def get_manager() -> ArtiqRpcClientManager:
    global _manager  # pylint: disable=global-statement
    with _manager_lock:
        if _manager is None:
            _manager = ArtiqRpcClientManager(
                settings.ARTIQ_MASTER_HOST,
                int(settings.ARTIQ_MASTER_PORT),
            )
        return _manager


def reset_rpc_manager() -> None:
    """Reset the process-wide manager. For tests and rare reload scenarios."""
    global _manager  # pylint: disable=global-statement
    with _manager_lock:
        _manager = None
