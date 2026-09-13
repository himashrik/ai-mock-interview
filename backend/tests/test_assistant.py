import uuid

from app.models.assistant import AssistantMessage
from app.services import assistant_service


def test_send_message_persists_both_user_and_assistant_turns(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.assistant_service")
    fake.text_response = "Try structuring your answer with the STAR method."

    user_id = uuid.uuid4()
    reply = assistant_service.send_message(db_session, user_id=user_id, message="How do I answer behavioral questions?")

    assert reply.role == "assistant"
    assert reply.content == "Try structuring your answer with the STAR method."

    history = assistant_service.get_history(db_session, user_id=user_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"


def test_send_message_falls_back_gracefully_on_llm_failure(db_session, monkeypatch):
    class BrokenLLM:
        def complete_text(self, *a, **kw):
            raise RuntimeError("upstream is down")

        def complete_json(self, *a, **kw):
            raise RuntimeError("upstream is down")

    monkeypatch.setattr("app.services.assistant_service.get_llm_provider", lambda: BrokenLLM())

    user_id = uuid.uuid4()
    reply = assistant_service.send_message(db_session, user_id=user_id, message="Help me with my resume")

    assert reply.role == "assistant"
    assert reply.content == assistant_service.FALLBACK_REPLY
    # the user's message must still be persisted even though the assistant call failed
    history = assistant_service.get_history(db_session, user_id=user_id)
    assert len(history) == 2


def test_send_message_includes_conversation_history_in_prompt(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.assistant_service")
    fake.text_response = "Sure, here's more detail."
    user_id = uuid.uuid4()

    assistant_service.send_message(db_session, user_id=user_id, message="What's the STAR method?")
    assistant_service.send_message(db_session, user_id=user_id, message="Can you give an example?")

    # second call's prompt should reference the first exchange
    _, _, second_prompt = fake.calls[1]
    assert "STAR method" in second_prompt


def test_get_history_is_scoped_per_user(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.assistant_service")
    fake.text_response = "reply"

    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    assistant_service.send_message(db_session, user_id=user_a, message="Question from A")
    assistant_service.send_message(db_session, user_id=user_b, message="Question from B")

    history_a = assistant_service.get_history(db_session, user_id=user_a)
    assert all(m.user_id == user_a for m in history_a)
    assert not any("Question from B" in m.content for m in history_a)


class TestAssistantApi:
    def test_send_and_fetch_messages_via_api(self, client, registered_user, patch_llm_provider):
        _, headers, _, _ = registered_user
        fake = patch_llm_provider("app.services.assistant_service")
        fake.text_response = "Here's my advice."

        resp = client.post("/assistant/messages", json={"message": "How should I prep for a system design round?"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "assistant"
        assert resp.json()["content"] == "Here's my advice."

        resp = client.get("/assistant/messages", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_assistant_messages_isolated_between_users(self, client, patch_llm_provider):
        fake = patch_llm_provider("app.services.assistant_service")
        fake.text_response = "reply"

        client.post("/auth/register", json={"email": "chatuser1@example.com", "password": "password123", "full_name": "U1"})
        login1 = client.post("/auth/login", json={"email": "chatuser1@example.com", "password": "password123"})
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        client.post("/auth/register", json={"email": "chatuser2@example.com", "password": "password123", "full_name": "U2"})
        login2 = client.post("/auth/login", json={"email": "chatuser2@example.com", "password": "password123"})
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        client.post("/assistant/messages", json={"message": "Secret question from user 1"}, headers=headers1)

        resp = client.get("/assistant/messages", headers=headers2)
        assert resp.status_code == 200
        assert resp.json() == []  # user 2 sees none of user 1's chat history

    def test_assistant_requires_authentication(self, client):
        resp = client.post("/assistant/messages", json={"message": "hi"})
        assert resp.status_code == 401

    def test_assistant_rejects_empty_message(self, client, registered_user):
        _, headers, _, _ = registered_user
        resp = client.post("/assistant/messages", json={"message": ""}, headers=headers)
        assert resp.status_code == 422
