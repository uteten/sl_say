from pathlib import Path

import pytest

from app.filter_config import FilterConfig, MatchRule, ReplaceRule


class TestMatchRule:
    def test_plain_contains(self) -> None:
        rule = MatchRule.parse("%")
        assert rule.matches("%3A%3AStatic") is True
        assert rule.matches("Normal User") is False

    def test_regex_match(self) -> None:
        rule = MatchRule.parse(r"re:^Object\b")
        assert rule.matches("Object Door") is True
        assert rule.matches("SomeObject") is False

    def test_invalid_regex_no_match(self) -> None:
        rule = MatchRule.parse("re:[invalid")
        assert rule.matches("anything") is False


class TestReplaceRule:
    def test_plain_replace(self) -> None:
        rule = ReplaceRule.parse("foo", "bar")
        assert rule.apply("foo baz foo") == "bar baz bar"

    def test_regex_replace(self) -> None:
        rule = ReplaceRule.parse("re:w$", "わら")
        assert rule.apply("面白いw") == "面白いわら"

    def test_regex_end_anchor_matches_trailing(self) -> None:
        rule = ReplaceRule.parse("re:w$", "わら")
        assert rule.apply("www") == "wwわら"

    def test_regex_no_match(self) -> None:
        rule = ReplaceRule.parse("re:w$", "わら")
        assert rule.apply("hello") == "hello"

    def test_regex_url_removal(self) -> None:
        rule = ReplaceRule.parse(r"re:https?://\S+", "")
        assert rule.apply("見て https://example.com すごい") == "見て  すごい"

    def test_invalid_regex_skipped(self) -> None:
        rule = ReplaceRule.parse("re:[invalid", "x")
        assert rule.is_regex is True
        assert rule._compiled is None
        assert rule.apply("test [invalid") == "test [invalid"

    def test_plain_empty_replacement(self) -> None:
        rule = ReplaceRule.parse("削除", "")
        assert rule.apply("これを削除する") == "これをする"


class TestFilterConfigLoad:
    def test_load_default_when_file_missing(self, tmp_path: Path) -> None:
        config = FilterConfig.load(tmp_path / "filters.txt")
        assert len(config.exclude_patterns) == 0
        assert len(config.exclude_speaker_rules) > 0

    def test_load_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "filters.txt"
        f.write_text(
            "[exclude_speaker]\n%\n[exclude]\nCustom\n[replace]\nfoo => bar\n",
            encoding="utf-8",
        )
        config = FilterConfig.load(f)
        assert len(config.exclude_speaker_rules) == 1
        assert config.exclude_speaker_rules[0].pattern == "%"
        assert len(config.exclude_patterns) == 1
        assert config.exclude_patterns[0].pattern == "Custom"
        assert len(config.replace_rules) == 1

    def test_load_regex_speaker_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "filters.txt"
        f.write_text(r"[exclude_speaker]" + "\n" + r"re:^Object\b" + "\n", encoding="utf-8")
        config = FilterConfig.load(f)
        assert config.exclude_speaker_rules[0].is_regex is True

    def test_load_ignores_comments_and_blanks(self, tmp_path: Path) -> None:
        f = tmp_path / "filters.txt"
        f.write_text(
            "# comment\n[exclude]\n# another comment\nPattern1\n\nPattern2\n",
            encoding="utf-8",
        )
        config = FilterConfig.load(f)
        assert len(config.exclude_patterns) == 2

    def test_load_replace_with_empty_right(self, tmp_path: Path) -> None:
        f = tmp_path / "filters.txt"
        f.write_text("[replace]\nremoveme =>\n", encoding="utf-8")
        config = FilterConfig.load(f)
        assert config.replace_rules[0].replacement == ""

    def test_load_replace_with_arrow_in_value(self, tmp_path: Path) -> None:
        f = tmp_path / "filters.txt"
        f.write_text("[replace]\na => b => c\n", encoding="utf-8")
        config = FilterConfig.load(f)
        assert config.replace_rules[0].replacement == "b => c"

    def test_load_regex_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "filters.txt"
        f.write_text("[replace]\nre:w$ => わら\n", encoding="utf-8")
        config = FilterConfig.load(f)
        assert config.replace_rules[0].is_regex is True


class TestFilterConfigSaveDefault:
    def test_save_default_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "filters.txt"
        FilterConfig.save_default(path)
        assert path.exists()
        config = FilterConfig.load(path)
        assert len(config.exclude_speaker_rules) > 0

    def test_save_default_contains_sample_rules(self, tmp_path: Path) -> None:
        path = tmp_path / "filters.txt"
        FilterConfig.save_default(path)
        config = FilterConfig.load(path)
        patterns = [r.pattern for r in config.replace_rules]
        assert "SL" in patterns


class TestFilterConfigApply:
    def test_should_exclude_by_speaker_percent(self) -> None:
        config = FilterConfig()
        assert config.should_exclude_speaker("%3A%3AStatic%3A%3A Wild Eye") is True

    def test_should_exclude_by_speaker_bracket(self) -> None:
        config = FilterConfig()
        assert config.should_exclude_speaker("Bite Marks [Bloodlines]") is True

    def test_should_not_exclude_normal_speaker(self) -> None:
        config = FilterConfig()
        assert config.should_exclude_speaker("obadasho") is False

    def test_should_exclude_custom_speaker(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[MatchRule.parse("Signboard")],
            exclude_patterns=[],
        )
        assert config.should_exclude_speaker("Signboard") is True
        assert config.should_exclude_speaker("User") is False

    def test_should_exclude_regex_speaker(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[MatchRule.parse(r"re:^Object\b")],
            exclude_patterns=[],
        )
        assert config.should_exclude_speaker("Object Door") is True
        assert config.should_exclude_speaker("SomeObject") is False

    def test_should_exclude_body_pattern(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[],
            exclude_patterns=[MatchRule.parse("Configuration Loaded")],
        )
        assert config.should_exclude_body("Configuration Loaded") is True

    def test_should_exclude_body_regex_pattern(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[],
            exclude_patterns=[MatchRule.parse(r"re:Memory Free:\s*\d+KiB")],
        )
        assert config.should_exclude_body("Memory Free: 8872KiB") is True
        assert config.should_exclude_body("こんにちは") is False

    def test_should_not_exclude_normal_body(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[],
            exclude_patterns=[MatchRule.parse("Configuration Loaded")],
        )
        assert config.should_exclude_body("こんにちは") is False

    def test_apply_plain_replacements(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[],
            exclude_patterns=[],
            replace_rules=[ReplaceRule.parse("ｗ", "わら")],
        )
        assert config.apply_replacements("面白いｗ") == "面白いわら"

    def test_apply_regex_replacements(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[],
            exclude_patterns=[],
            replace_rules=[ReplaceRule.parse("re:w$", "わら")],
        )
        assert config.apply_replacements("面白いw") == "面白いわら"

    def test_apply_mixed_replacements(self) -> None:
        config = FilterConfig(
            exclude_speaker_rules=[],
            exclude_patterns=[],
            replace_rules=[
                ReplaceRule.parse("SL", "Second Life"),
                ReplaceRule.parse("re:w$", "わら"),
            ],
        )
        assert config.apply_replacements("SLで遊んだw") == "Second Lifeで遊んだわら"
