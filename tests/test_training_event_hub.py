import queue


def test_training_event_hub_broadcasts_independently_and_unregisters():
    from src.training.api import TrainingEventHub

    hub = TrainingEventHub(queue_size=2)
    first = hub.subscribe()
    second = hub.subscribe()

    hub.publish({"type": "step", "step": 1})

    assert first.get_nowait() == {"type": "step", "step": 1}
    assert second.get_nowait() == {"type": "step", "step": 1}

    hub.unsubscribe(first)
    hub.publish({"type": "step", "step": 2})

    with __import__("pytest").raises(queue.Empty):
        first.get_nowait()
    assert second.get_nowait() == {"type": "step", "step": 2}


def test_training_event_hub_drops_only_the_slow_subscriber_when_full():
    from src.training.api import TrainingEventHub

    hub = TrainingEventHub(queue_size=1)
    slow = hub.subscribe()
    fast = hub.subscribe()

    slow.put_nowait({"type": "old"})
    hub.publish({"type": "new"})

    assert slow.get_nowait() == {"type": "old"}
    assert fast.get_nowait() == {"type": "new"}
