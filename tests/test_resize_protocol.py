import asyncio
import unittest
from unittest.mock import AsyncMock, Mock
from takeover.native_broker import Broker, layout_request, resolution_request


class ResizeProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_coalesced_resize_does_not_release_lease(self):
        desktop = Mock(revoked=asyncio.Event(), state=AsyncMock(return_value='remote'))
        layout = Mock()
        broker = Broker(desktop, '/session', layout)
        reader = asyncio.StreamReader()
        task = asyncio.create_task(broker.read_updates(reader))
        reader.feed_data(b'RESIZE 1280 720\nRESIZE 1920 1080\n')
        await asyncio.sleep(.2)
        layout.resize.assert_called_once_with(1920, 1080)
        self.assertFalse(task.done())
        reader.feed_eof()
        await task

    async def test_disconnect_discards_pending_resize(self):
        desktop = Mock(revoked=asyncio.Event(), state=AsyncMock(return_value='remote'))
        layout = Mock()
        reader = asyncio.StreamReader()
        reader.feed_data(b'RESIZE 1920 1080\n')
        reader.feed_eof()
        await Broker(desktop, '/session', layout).read_updates(reader)
        layout.resize.assert_not_called()

    async def test_revoked_session_cannot_resize(self):
        desktop = Mock(revoked=asyncio.Event(), state=AsyncMock(return_value='remote'))
        desktop.revoked.set()
        layout = Mock()
        reader = asyncio.StreamReader()
        task = asyncio.create_task(Broker(desktop, '/session', layout).read_updates(reader))
        reader.feed_data(b'RESIZE 1920 1080\n')
        await asyncio.sleep(.2)
        reader.feed_eof()
        await task
        layout.resize.assert_not_called()

    async def test_layout_carries_extra_monitors_and_coalesces(self):
        desktop = Mock(revoked=asyncio.Event(), state=AsyncMock(return_value='remote'))
        layout = Mock()
        reader = asyncio.StreamReader()
        task = asyncio.create_task(Broker(desktop, '/session', layout).read_updates(reader))
        reader.feed_data(b'LAYOUT 1920 1080 1920 0 1280 1024\nLAYOUT 1920 1080 -1920 0 1920 1080\n')
        await asyncio.sleep(.2)
        layout.resize.assert_called_once_with(1920, 1080, extras=((-1920, 0, 1920, 1080),))
        reader.feed_eof()
        await task

    async def test_resize_after_layout_drops_extra_monitors(self):
        desktop = Mock(revoked=asyncio.Event(), state=AsyncMock(return_value='remote'))
        layout = Mock()
        reader = asyncio.StreamReader()
        task = asyncio.create_task(Broker(desktop, '/session', layout).read_updates(reader))
        reader.feed_data(b'LAYOUT 1920 1080 1920 0 1280 1024\nRESIZE 1280 720\n')
        await asyncio.sleep(.2)
        layout.resize.assert_called_once_with(1280, 720)
        reader.feed_eof()
        await task

    async def test_rejected_layout_keeps_lease_and_last_valid_layout(self):
        desktop = Mock(revoked=asyncio.Event(), state=AsyncMock(return_value='remote'))
        layout = Mock()
        reader = asyncio.StreamReader()
        task = asyncio.create_task(Broker(desktop, '/session', layout).read_updates(reader))
        reader.feed_data(b'LAYOUT 1920 1080 0 0 100 100\n')
        await asyncio.sleep(.2)
        layout.resize.assert_not_called()
        self.assertFalse(task.done())
        reader.feed_data(b'LAYOUT 1920 1080 1920 0 1280 1024\nLAYOUT 1920 1080 70000 0 1280 1024\n')
        await asyncio.sleep(.2)
        layout.resize.assert_called_once_with(1920, 1080, extras=((1920, 0, 1280, 1024),))
        reader.feed_eof()
        await task

    def test_layout_request_validation(self):
        self.assertEqual(layout_request(b'REMOTE 1920 1080\n', (b'REMOTE',)),
                         (b'REMOTE', (1920, 1080), ()))
        self.assertEqual(layout_request(b'REMOTE 2560 1440 0 -1080 1920 1080', (b'REMOTE',))[2],
                         ((0, -1080, 1920, 1080),))
        for request in [b'LAYOUT 1920 1080 0 0 1920', b'LAYOUT 1920 1080 0 0 100 100',
                        b'LAYOUT 1920 1080 70000 0 1920 1080', b'RESIZE 1920 1080 0 0 1920 1080',
                        b'LAYOUT 1920 1080' + b' 1920 0 1920 1080' * 4, b'LAYOUT', b'']:
            with self.assertRaises(ValueError):
                verbs = (b'LAYOUT',) if not request.startswith(b'RESIZE') else (b'RESIZE',)
                if request.startswith(b'RESIZE'):
                    resolution_request(request, b'RESIZE')
                else:
                    layout_request(request, verbs)

    async def test_invalid_dimensions_rejected(self):
        for request in [b'RESIZE 0 720', b'RESIZE -1 720', b'RESIZE 9000 1000', b'RESIZE nan 900']:
            with self.assertRaises(ValueError):
                resolution_request(request, b'RESIZE')


if __name__ == '__main__':
    unittest.main()
