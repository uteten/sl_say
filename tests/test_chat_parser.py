import pytest

from app.chat_parser import ChatMessage, ChatParser


class TestChatParser:
    def setup_method(self) -> None:
        self.parser = ChatParser()

    def test_parse_macos_12h_format(self) -> None:
        line = "[2026/04/24 8:13 午前]  uten Resident: こんにちは"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "uten Resident"
        assert result.body == "こんにちは"
        assert result.message_type == "say"

    def test_parse_macos_12h_pm_format(self) -> None:
        line = "[2026/04/24 2:30 午後]  uten Resident: テスト"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "uten Resident"
        assert result.body == "テスト"

    def test_parse_say_message_japanese(self) -> None:
        line = "[2026/03/26 14:05]  Kokoro Resident: こんにちは！"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "Kokoro Resident"
        assert result.body == "こんにちは！"
        assert result.message_type == "say"

    def test_parse_shout_message(self) -> None:
        line = "[2026/03/26 14:06]  Kokoro Resident shouts: 聞こえますか？"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "Kokoro Resident"
        assert result.body == "聞こえますか？"
        assert result.message_type == "shout"

    def test_parse_whisper_message(self) -> None:
        line = "[2026/03/26 14:06]  Kokoro Resident whispers: ここだよ"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "Kokoro Resident"
        assert result.body == "ここだよ"
        assert result.message_type == "whisper"

    def test_parse_emote_message(self) -> None:
        line = "[2026/03/26 14:07]  Kokoro Resident waves hello."
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "Kokoro Resident"
        assert result.message_type == "emote"

    def test_parse_timestamp_with_seconds(self) -> None:
        line = "[2026/03/26 14:05:30]  Kokoro Resident: こんにちは"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "Kokoro Resident"
        assert result.body == "こんにちは"

    def test_filter_system_message(self) -> None:
        line = "[2026/03/26 14:09]  Second Life: Teleport completed"
        result = self.parser.parse_line(line)
        assert result is None

    def test_filter_empty_line(self) -> None:
        result = self.parser.parse_line("")
        assert result is None

    def test_filter_whitespace_line(self) -> None:
        result = self.parser.parse_line("   ")
        assert result is None

    def test_continuation_line_without_timestamp(self) -> None:
        line = "this is a continuation line"
        result = self.parser.parse_line(line)
        assert result is None

    def test_japanese_message(self) -> None:
        line = "[2026/03/26 14:05]  ユーザー名: こんにちは！"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "ユーザー名"
        assert result.body == "こんにちは！"

    def test_allow_english_message(self) -> None:
        line = "[2026/03/26 14:05]  User: Hello everyone!"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "User"
        assert result.body == "Hello everyone!"

    def test_filter_object_speaker_with_percent(self) -> None:
        line = "[2026/03/26 14:05]  %3A%3AStatic%3A%3A Wild Eye: Configuration Loaded"
        result = self.parser.parse_line(line)
        assert result is None

    def test_filter_object_speaker_with_bracket(self) -> None:
        line = "[2026/03/26 14:05]  Bite Marks [Bloodlines] 2.2: new version available"
        result = self.parser.parse_line(line)
        assert result is None

    def test_filter_body_exclude_pattern(self) -> None:
        from app.filter_config import FilterConfig, MatchRule
        fc = FilterConfig(exclude_speaker_rules=[], exclude_patterns=[MatchRule.parse("Configuration Loaded")], replace_rules=[])
        parser = ChatParser(filter_config=fc)
        line = "[2026/03/26 14:05]  SomeObject: Configuration Loaded"
        result = parser.parse_line(line)
        assert result is None

    def test_allow_normal_speaker_with_parens(self) -> None:
        line = "[2026/03/26 14:05]  Mr. Pickle (obadasho): hi uten"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.speaker == "Mr. Pickle"

    def test_exclude_speaker_checks_parens_content(self) -> None:
        """括弧付き発言者の場合、括弧内のIDで除外判定する"""
        from app.filter_config import FilterConfig, MatchRule
        fc = FilterConfig(
            exclude_speaker_rules=[MatchRule.parse("badbot")],
            exclude_patterns=[],
        )
        parser = ChatParser(filter_config=fc)
        # 括弧内がマッチ → 除外
        line = "[2026/03/26 14:05]  Nice Name (badbot): hello"
        assert parser.parse_line(line) is None
        # 括弧外はチェック対象外 → 通過
        line2 = "[2026/03/26 14:05]  badbot (goodid): hello"
        result = parser.parse_line(line2)
        assert result is not None
        assert result.speaker == "badbot"

    def test_exclude_speaker_no_parens_checks_full_name(self) -> None:
        """括弧なし発言者の場合、全体で除外判定する"""
        from app.filter_config import FilterConfig, MatchRule
        fc = FilterConfig(
            exclude_speaker_rules=[MatchRule.parse("Signboard")],
            exclude_patterns=[],
        )
        parser = ChatParser(filter_config=fc)
        line = "[2026/03/26 14:05]  Signboard: ちりこ [700m]"
        assert parser.parse_line(line) is None

    def test_message_with_colon_in_body(self) -> None:
        line = "[2026/03/26 14:05]  User: 時刻は14:30です"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.body == "時刻は14:30です"

    def test_crlf_line(self) -> None:
        line = "[2026/03/26 14:05]  User: こんにちは\r\n"
        result = self.parser.parse_line(line)
        assert result is not None
        assert result.body == "こんにちは"

    def test_filter_online_notification(self) -> None:
        from app.filter_config import FilterConfig, MatchRule
        fc = FilterConfig(exclude_speaker_rules=[], exclude_patterns=[MatchRule.parse("はオンラインです。")])
        parser = ChatParser(filter_config=fc)
        line = "[2026/03/26 14:05]  User: はオンラインです。"
        assert parser.parse_line(line) is None

    def test_filter_offline_notification(self) -> None:
        from app.filter_config import FilterConfig, MatchRule
        fc = FilterConfig(exclude_speaker_rules=[], exclude_patterns=[MatchRule.parse("はオフラインです。")])
        parser = ChatParser(filter_config=fc)
        line = "[2026/03/26 14:05]  User: はオフラインです。"
        assert parser.parse_line(line) is None
