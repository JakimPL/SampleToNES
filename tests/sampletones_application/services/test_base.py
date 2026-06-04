from typing import List
from unittest.mock import MagicMock, call, patch

import pytest

from sampletones_application.services.base import ServiceBase
from sampletones_application.utils.callbacks.queue import CallbackQueue


class _ConcreteService(ServiceBase[int]):
    def emit(self, value: int) -> None:
        self._emit(value)


class TestServiceBaseSubscription:
    def test_subscriber_receives_emitted_result(self) -> None:
        service = _ConcreteService()
        results: List[int] = []
        service.subscribe(results.append)

        service.emit(42)

        assert results == [42]

    def test_unsubscribed_handler_not_called(self) -> None:
        service = _ConcreteService()
        results: List[int] = []
        service.subscribe(results.append)
        service.unsubscribe(results.append)

        service.emit(1)

        assert results == []

    def test_multiple_subscribers_all_receive_result(self) -> None:
        service = _ConcreteService()
        received_a: List[int] = []
        received_b: List[int] = []
        received_c: List[int] = []
        service.subscribe(received_a.append)
        service.subscribe(received_b.append)
        service.subscribe(received_c.append)

        service.emit(7)

        assert received_a == [7]
        assert received_b == [7]
        assert received_c == [7]

    def test_duplicate_subscriber_called_once_per_registration(self) -> None:
        service = _ConcreteService()
        handler = MagicMock()
        service.subscribe(handler)
        service.subscribe(handler)

        service.emit(5)

        assert handler.call_count == 2

    def test_unsubscribe_nonexistent_handler_is_safe(self) -> None:
        service = _ConcreteService()
        handler = MagicMock()

        service.unsubscribe(handler)

    def test_emit_calls_subscribers_in_subscription_order(self) -> None:
        service = _ConcreteService()
        call_order: List[str] = []
        service.subscribe(lambda _: call_order.append("first"))
        service.subscribe(lambda _: call_order.append("second"))

        service.emit(0)

        assert call_order == ["first", "second"]

    def test_no_emission_before_subscribe(self) -> None:
        service = _ConcreteService()
        results: List[int] = []

        service.emit(99)

        service.subscribe(results.append)
        assert results == []

    def test_multiple_emissions_all_delivered(self) -> None:
        service = _ConcreteService()
        results: List[int] = []
        service.subscribe(results.append)

        service.emit(1)
        service.emit(2)
        service.emit(3)

        assert results == [1, 2, 3]


class TestServiceBaseCallbackQueueIntegration:
    def test_emit_passes_priority_to_callback_queue(self) -> None:
        service = _ConcreteService(priority=5)
        handler = MagicMock()
        service.subscribe(handler)

        with patch.object(CallbackQueue, "add") as mock_add:
            service._emit(10)

        mock_add.assert_called_once_with(handler, 10, priority=5)

    def test_emit_queues_each_listener_separately(self) -> None:
        service = _ConcreteService(priority=3)
        handler_a = MagicMock()
        handler_b = MagicMock()
        service.subscribe(handler_a)
        service.subscribe(handler_b)

        with patch.object(CallbackQueue, "add") as mock_add:
            service._emit(20)

        assert mock_add.call_count == 2
        mock_add.assert_has_calls(
            [call(handler_a, 20, priority=3), call(handler_b, 20, priority=3)],
            any_order=False,
        )

    def test_zero_listeners_no_queue_calls(self) -> None:
        service = _ConcreteService()

        with patch.object(CallbackQueue, "add") as mock_add:
            service._emit(0)

        mock_add.assert_not_called()
