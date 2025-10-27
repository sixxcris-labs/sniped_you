from app.notifier import telegram, discord


def test_telegram_send_mock(monkeypatch):
    """Checks that the Telegram notifier works with a mock call."""
    called = {}

    def fake_send_message(chat_id, text, photo_path=None):
        called["chat_id"] = chat_id
        called["text"] = text
        called["photo_path"] = photo_path
        print(f"[Mock] Telegram send: {text}")
        return {"ok": True}

    monkeypatch.setattr(telegram, "send_message", fake_send_message)

    result = telegram.send_message(
        chat_id=1234, text="Mock Alert", photo_path="mock.png"
    )
    assert result["ok"] is True
    assert called["chat_id"] == 1234
    assert "Mock Alert" in called["text"]


def test_discord_send_mock(monkeypatch):
    """Checks that the Discord notifier works with a mock call."""
    sent = {}

    def fake_send_message(webhook_url, content, image_url=None):
        sent["webhook_url"] = webhook_url
        sent["content"] = content
        sent["image_url"] = image_url
        print(f"[Mock] Discord send: {content}")
        return {"ok": True}

    monkeypatch.setattr(discord, "send_message", fake_send_message)

    result = discord.send_message(
        "https://mock.discord/api", "Mock content", "mock.jpg"
    )
    assert result["ok"] is True
    assert "mock.discord" in sent["webhook_url"]
    assert "Mock content" in sent["content"]
