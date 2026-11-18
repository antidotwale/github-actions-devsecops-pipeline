from app import app


def test_health():
    r = app.test_client().get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_add():
    r = app.test_client().get("/add?a=2&b=3")
    assert r.get_json() == {"result": 5}


def test_add_rejects_bad_input():
    r = app.test_client().get("/add?a=x&b=3")
    assert r.status_code == 400
