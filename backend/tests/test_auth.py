import sys
import os
import types
import asyncio

import pytest

# Ensure 'backend' parent dir on sys.path
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient

from app import db as app_db
from app import main as app_main


class FakeUsersCollection:
    def __init__(self):
        self.by_id = {}
        self.by_username = {}

    async def find_one(self, query):
        if "_id" in query:
            return self.by_id.get(query["_id"]) or None
        if "username" in query:
            return self.by_username.get(query["username"]) or None
        return None

    async def insert_one(self, doc):
        # simulate unique username constraint
        if doc["username"] in self.by_username:
            raise Exception("duplicate username")
        self.by_id[doc["_id"]] = doc
        self.by_username[doc["username"]] = doc
        return types.SimpleNamespace(inserted_id=doc["_id"]) 

    async def create_index(self, *args, **kwargs):
        return None


class FakeMessagesCollection:
    async def create_index(self, *args, **kwargs):
        return None


@pytest.fixture
def client(monkeypatch):
    users = FakeUsersCollection()
    messages = FakeMessagesCollection()

    async def fake_connect():
        app_db.users_collection = users
        app_db.messages_collection = messages

    async def fake_close():
        app_db.users_collection = None
        app_db.messages_collection = None

    # Ensure SECRET_KEY is set for JWT
    monkeypatch.setenv("SECRET_KEY", "testsecret")

    # Patch the bound functions in main module (startup/shutdown)
    monkeypatch.setattr(app_main, "connect_to_mongo", fake_connect)
    monkeypatch.setattr(app_main, "close_mongo_connection", fake_close)

    with TestClient(app_main.app) as c:
        yield c


def test_register_login_me_flow(client):
    # Register
    r = client.post("/register", json={"username": "alice", "password": "secret123", "email": "a@example.com"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["username"] == "alice"
    assert "_id" in data

    # Duplicate register should fail
    r2 = client.post("/register", json={"username": "alice", "password": "secret123"})
    assert r2.status_code == 400

    # Login
    r3 = client.post("/login", json={"username": "alice", "password": "secret123"})
    assert r3.status_code == 200, r3.text
    tok = r3.json()["access_token"]
    assert tok

    # /me
    r4 = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r4.status_code == 200
    me = r4.json()
    assert me["username"] == "alice"

    # Wrong password
    r5 = client.post("/login", json={"username": "alice", "password": "wrong"})
    assert r5.status_code == 401
