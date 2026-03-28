import time
from unittest.mock import MagicMock

from app.chat_parser import ChatMessage
from app.tts_queue import TTSQueue


class TestTTSQueue:
    def test_enqueue_and_process(self) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = "/tmp/fake.mp3"
        mock_player = MagicMock()
        mock_player.play.return_value = True

        queue = TTSQueue(mock_engine, mock_player)
        queue.start()

        msg = ChatMessage(speaker="User", body="Hello", message_type="say")
        queue.enqueue(msg)
        time.sleep(1)
        queue.stop()

        mock_engine.synthesize.assert_called_once_with("User: Hello")
        mock_player.play.assert_called_once_with("/tmp/fake.mp3")

    def test_multiple_messages_processed_in_order(self) -> None:
        call_order: list[str] = []
        mock_engine = MagicMock()
        mock_engine.synthesize.side_effect = lambda text: (call_order.append(text), "/tmp/fake.mp3")[1]
        mock_player = MagicMock()
        mock_player.play.return_value = True

        queue = TTSQueue(mock_engine, mock_player)
        queue.start()

        queue.enqueue(ChatMessage(speaker="A", body="first", message_type="say"))
        queue.enqueue(ChatMessage(speaker="B", body="second", message_type="say"))
        time.sleep(1.5)
        queue.stop()

        assert call_order == ["A: first", "B: second"]

    def test_tts_error_continues_processing(self) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.side_effect = [None, "/tmp/ok.mp3"]
        mock_player = MagicMock()
        mock_player.play.return_value = True

        queue = TTSQueue(mock_engine, mock_player)
        queue.start()

        queue.enqueue(ChatMessage(speaker="A", body="fail", message_type="say"))
        queue.enqueue(ChatMessage(speaker="B", body="ok", message_type="say"))
        time.sleep(1.5)
        queue.stop()

        mock_player.play.assert_called_once_with("/tmp/ok.mp3")

    def test_emote_text_format(self) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = "/tmp/fake.mp3"
        mock_player = MagicMock()
        mock_player.play.return_value = True

        queue = TTSQueue(mock_engine, mock_player)
        queue.start()

        queue.enqueue(ChatMessage(speaker="User", body="waves", message_type="emote"))
        time.sleep(1)
        queue.stop()

        mock_engine.synthesize.assert_called_once_with("User waves")
