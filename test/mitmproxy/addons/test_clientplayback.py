import asyncio
import ssl
from contextlib import asynccontextmanager

import pytest

from mitmproxy.addons.clientplayback import ClientPlayback
from mitmproxy.addons.clientplayback import ReplayHandler
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.addons.tlsconfig import TlsConfig
from mitmproxy.connection import Address
from mitmproxy.exceptions import CommandError
from mitmproxy.exceptions import OptionsError
from mitmproxy.test import taddons
from mitmproxy.test import tflow


@asynccontextmanager
async def tcp_server(handle_conn, **server_args) -> Address:
    """TCP server context manager that...

    1. Exits only after all handlers have returned.
    2. Ensures that all handlers are closed properly. If we don't do that,
       we get ghost errors in others tests from StreamWriter.__del__.

    Spawning a TCP server is relatively slow. Consider using in-memory networking for faster tests.
    """
    if not hasattr(asyncio, "TaskGroup"):
        pytest.skip("Skipped because asyncio.TaskGroup is unavailable.")

    tasks = asyncio.TaskGroup()

    async def handle_conn_wrapper(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            await handle_conn(reader, writer)
        except Exception as e:
            print(f"!!! TCP handler failed: {e}")
            raise
        finally:
            if not writer.is_closing():
                writer.close()
            await writer.wait_closed()

    async def _handle(r, w):
        tasks.create_task(handle_conn_wrapper(r, w))

    server = await asyncio.start_server(_handle, "127.0.0.1", 0, **server_args)
    await server.start_serving()
    async with server:
        async with tasks:
            yield server.sockets[0].getsockname()


@pytest.mark.parametrize("mode", ["http", "https", "upstream", "err"])
@pytest.mark.parametrize("concurrency", [-1, 1])
async def test_playback(tdata, mode, concurrency):
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if mode == "err":
            return
        req = await reader.readline()
        if mode == "upstream":
            assert req == b"GET http://address:22/path HTTP/1.1\r\n"
        else:
            assert req == b"GET /path HTTP/1.1\r\n"
        req = await reader.readuntil(b"data")
        assert req == (
            b"header: qvalue\r\n"
            b"content-length: 4\r\nHost: example.mitmproxy.org\r\n\r\n"
            b"data"
        )
        writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
        await writer.drain()
        assert not await reader.read()

    cp = ClientPlayback()
    ps = Proxyserver()
    tls = TlsConfig()
    with taddons.context(cp, ps, tls) as tctx:
        tctx.configure(cp, client_replay_concurrency=concurrency)

        server_args = {}
        if mode == "https":
            server_args["ssl"] = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            server_args["ssl"].load_cert_chain(
                certfile=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-leaf.crt"
                ),
                keyfile=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-leaf.key"
                ),
            )
            tctx.configure(
                tls,
                ssl_verify_upstream_trusted_ca=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-root.crt"
                ),
            )

        async with tcp_server(handler, **server_args) as addr:
            cp.running()
            flow = tflow.tflow(live=False)
            flow.request.content = b"data"
            if mode == "upstream":
                tctx.options.mode = [f"upstream:http://{addr[0]}:{addr[1]}"]
                flow.request.authority = f"{addr[0]}:{addr[1]}"
                flow.request.host, flow.request.port = "address", 22
            else:
                flow.request.host, flow.request.port = addr
            if mode == "https":
                flow.request.scheme = "https"
            # Used for SNI
            flow.request.host_header = "example.mitmproxy.org"
            cp.start_replay([flow])
            assert cp.count() == 1
            await asyncio.wait_for(cp.queue.join(), 5)
            while cp.replay_tasks:
                await asyncio.sleep(0.001)
        if mode != "err":
            assert flow.response.status_code == 204
        await cp.done()


async def test_playback_https_upstream():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        conn_req = await reader.readuntil(b"\r\n\r\n")
        assert conn_req == b"CONNECT address:22 HTTP/1.1\r\nHost: address:22\r\n\r\n"
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        await writer.drain()
        assert not await reader.read()

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps) as tctx:
        tctx.configure(cp)
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.tflow(live=False)
            flow.request.scheme = b"https"
            flow.request.content = b"data"
            tctx.options.mode = [f"upstream:http://{addr[0]}:{addr[1]}"]
            cp.start_replay([flow])
            assert cp.count() == 1
            await asyncio.wait_for(cp.queue.join(), 5)

        assert flow.response is None
        assert (
            str(flow.error)
            == f"Upstream proxy {addr[0]}:{addr[1]} refused HTTP CONNECT request: 502 Bad Gateway"
        )
        await cp.done()


async def test_playback_crash(monkeypatch, caplog_async):
    async def raise_err(*_, **__):
        raise ValueError("oops")

    monkeypatch.setattr(ReplayHandler, "replay", raise_err)
    cp = ClientPlayback()
    with taddons.context(cp):
        cp.running()
        cp.start_replay([tflow.tflow(live=False)])
        await caplog_async.await_log("Client replay has crashed!")
        assert "oops" in caplog_async.caplog.text
        assert cp.count() == 0
        await cp.done()


def test_check():
    cp = ClientPlayback()
    f = tflow.tflow(resp=True)
    f.live = True
    assert "live flow" in cp.check(f)

    f = tflow.tflow(resp=True, live=False)
    f.intercepted = True
    assert "intercepted flow" in cp.check(f)

    f = tflow.tflow(resp=True, live=False)
    f.request = None
    assert "missing request" in cp.check(f)

    f = tflow.tflow(resp=True, live=False)
    f.request.raw_content = None
    assert "missing content" in cp.check(f)

    for f in (tflow.ttcpflow(), tflow.tudpflow()):
        f.live = False
        assert "Can only replay HTTP" in cp.check(f)


async def test_start_stop(tdata, caplog_async):
    cp = ClientPlayback()
    with taddons.context(cp):
        cp.start_replay([tflow.tflow(live=False)])
        assert cp.count() == 1

        ws_flow = tflow.twebsocketflow()
        ws_flow.live = False
        cp.start_replay([ws_flow])
        await caplog_async.await_log("Can't replay WebSocket flows.")
        assert cp.count() == 1

        cp.stop_replay()
        assert cp.count() == 0


def test_load(tdata):
    cp = ClientPlayback()
    with taddons.context(cp):
        cp.load_file(tdata.path("mitmproxy/data/dumpfile-018.mitm"))
        assert cp.count() == 1

        with pytest.raises(CommandError):
            cp.load_file("/nonexistent")
        assert cp.count() == 1


def test_configure(tdata):
    cp = ClientPlayback()
    with taddons.context(cp) as tctx:
        assert cp.count() == 0
        tctx.configure(
            cp, client_replay=[tdata.path("mitmproxy/data/dumpfile-018.mitm")]
        )
        assert cp.count() == 1
        tctx.configure(cp, client_replay=[])
        with pytest.raises(OptionsError):
            tctx.configure(cp, client_replay=["nonexistent"])
        tctx.configure(cp, client_replay_concurrency=-1)
        with pytest.raises(OptionsError):
            tctx.configure(cp, client_replay_concurrency=-2)
