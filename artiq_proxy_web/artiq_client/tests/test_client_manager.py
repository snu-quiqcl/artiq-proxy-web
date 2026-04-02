from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from artiq_client.client_manager import (
    ArtiqRpcClientManager,
    reset_rpc_manager,
)


class ArtiqRpcClientManagerTests(TestCase):
    @patch("artiq_client.client_manager.rpc.Client")
    def test_reuses_client_per_target(self, mock_client_class: MagicMock) -> None:
        mock_client_class.return_value = MagicMock()
        mgr = ArtiqRpcClientManager("::1", 3251)
        a1 = mgr.get_client("master_schedule")
        a2 = mgr.get_client("master_schedule")
        self.assertIs(a1, a2)
        self.assertEqual(mock_client_class.call_count, 1)
        mock_client_class.assert_called_once_with("::1", 3251, "master_schedule")

    @patch("artiq_client.client_manager.rpc.Client")
    def test_distinct_client_per_target_name(self, mock_client_class: MagicMock) -> None:
        mock_client_class.side_effect = lambda *args: MagicMock()
        mgr = ArtiqRpcClientManager("::1", 3251)
        mgr.get_client("master_schedule")
        mgr.get_client("master_experiment_db")
        self.assertEqual(mock_client_class.call_count, 2)

    @patch("artiq_client.client_manager.rpc.Client")
    def test_reset_client_recreates(self, mock_client_class: MagicMock) -> None:
        mock_client_class.return_value = MagicMock()
        mgr = ArtiqRpcClientManager("::1", 3251)
        mgr.get_client("a")
        mgr.reset_client("a")
        mgr.get_client("a")
        self.assertEqual(mock_client_class.call_count, 2)


@override_settings(ARTIQ_MASTER_HOST="10.0.0.1", ARTIQ_MASTER_PORT=9999)
class GetArtiqRpcClientTests(TestCase):
    def tearDown(self) -> None:
        reset_rpc_manager()
        super().tearDown()

    @patch("artiq_client.client_manager.rpc.Client")
    def test_get_artiq_rpc_client_uses_settings(self, mock_client_class: MagicMock) -> None:
        mock_client_class.return_value = MagicMock()
        from artiq_client.rpc import get_artiq_rpc_client

        get_artiq_rpc_client("master_schedule")
        mock_client_class.assert_called_once_with(
            "10.0.0.1", 9999, "master_schedule"
        )

    @patch("artiq_client.client_manager.rpc.Client")
    def test_get_artiq_rpc_client_reuses_singleton_manager(
        self, mock_client_class: MagicMock
    ) -> None:
        mock_client_class.return_value = MagicMock()
        from artiq_client.rpc import get_artiq_rpc_client

        get_artiq_rpc_client("x")
        get_artiq_rpc_client("x")
        self.assertEqual(mock_client_class.call_count, 1)
