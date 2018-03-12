'''Unit test fixtures'''
from pytest import fixture

from flashfocus.server import FlashServer

from test.helpers import WindowSession


@fixture
def windows():
    '''A display session with multiple open windows'''
    windows = WindowSession()
    yield windows.ids
    windows.destroy()


@fixture
def window():
    '''A single blank window'''
    windows = WindowSession()
    yield windows.ids[0]
    windows.destroy()


@fixture
def server():
    return FlashServer(opacity=0.8, time=0.05)
