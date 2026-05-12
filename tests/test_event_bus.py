import asyncio
import pytest
from app.services import event_bus


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    loop = asyncio.get_event_loop()
    event_bus.init(loop)

    q = event_bus.subscribe("project:abc")
    event_bus.publish("project:abc", {"msg": "hello", "level": "info"})

    await asyncio.sleep(0)  # let call_soon_threadsafe fire
    assert not q.empty()
    evt = q.get_nowait()
    assert evt["msg"] == "hello"

    event_bus.unsubscribe("project:abc", q)


@pytest.mark.asyncio
async def test_publish_to_unknown_key_is_noop():
    loop = asyncio.get_event_loop()
    event_bus.init(loop)
    event_bus.publish("project:missing", {"msg": "x"})  # must not raise


@pytest.mark.asyncio
async def test_unsubscribe_removes_queue():
    loop = asyncio.get_event_loop()
    event_bus.init(loop)

    q = event_bus.subscribe("task:xyz")
    event_bus.unsubscribe("task:xyz", q)
    event_bus.publish("task:xyz", {"msg": "after unsub"})
    await asyncio.sleep(0)
    assert q.empty()
