from nidibot.nitrado import Nitrado

nitrado_api_token = ""


def test_nitrado_api_availability():
    nitrado = Nitrado(nitrado_api_token)
    assert nitrado.is_api_available()


def test_nitrado_maintenance():
    nitrado = Nitrado(nitrado_api_token)
    assert not nitrado.is_maintenance_ongoing()


def test_gameserver_statuses():
    nitrado = Nitrado(nitrado_api_token)
    assert len(nitrado.get_statuses()) > 0


def test_gameserver_start():
    nitrado = Nitrado(nitrado_api_token)
    assert nitrado.start()


def test_gameserver_stop():
    nitrado = Nitrado(nitrado_api_token)
    assert nitrado.stop()


def test_gameserver_restart():
    nitrado = Nitrado(nitrado_api_token)
    assert nitrado.restart()
