import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_RE_PREFIX = "re:"

_DEFAULT_EXCLUDE_SPEAKER = ["%", "[", "{", "}"]

_DEFAULT_EXCLUDE_PATTERNS: list[str] = []

_DEFAULT_FILTERS_CONTENT = """\
# sl_say フィルタ設定
# 初期設定に戻したい場合は、このファイルを削除してからsl_sayを再起動してください。
#
# 発言本文除外（発言本文にこの文字列が含まれる場合、読み上げスキップ）
# 例:
# testaaa
# testbbb
[exclude]

# 置換ルール（読み上げ時に左辺を右辺に置換。右辺が空なら削除）
# 書式: 置換前 => 置換後
# 正規表現置換（re: プレフィックス付き）
[replace]
SL => Second Life
re:w$ => わら
re:https?://\\S+ =>

# 発言者名除外（オブジェクト等モノの発言をスキップする）
# 発言者名が「表示名 (ID)」形式の場合、括弧内のIDで判定する
# 括弧がない場合は発言者名全体で判定する
# re: プレフィックスで正規表現も使用可能
#
# デフォルト値:
#   % — URLエンコード文字を含むオブジェクト名（例: %3A%3AStatic%3A%3A Wild Eye）
#   [ — スクリプト付きオブジェクト名（例: Bite Marks [Bloodlines]）
#   { — スクリプト識別子を含むオブジェクト名
#   } — スクリプト識別子を含むオブジェクト名
[exclude_speaker]
%
[
{
}
"""


@dataclass
class MatchRule:
    """文字列含有チェックまたは正規表現マッチのルール."""

    pattern: str
    is_regex: bool = False
    _compiled: re.Pattern[str] | None = field(default=None, repr=False, compare=False)

    def matches(self, text: str) -> bool:
        if self.is_regex:
            if self._compiled is None:
                return False
            return bool(self._compiled.search(text))
        return self.pattern in text

    @staticmethod
    def parse(raw: str) -> "MatchRule":
        if raw.startswith(_RE_PREFIX):
            regex_str = raw[len(_RE_PREFIX):]
            try:
                compiled = re.compile(regex_str)
            except re.error as e:
                logger.warning("無効な正規表現をスキップ: %s (%s)", regex_str, e)
                return MatchRule(pattern=regex_str, is_regex=True, _compiled=None)
            return MatchRule(pattern=regex_str, is_regex=True, _compiled=compiled)
        return MatchRule(pattern=raw)


@dataclass
class ReplaceRule:
    pattern: str
    replacement: str
    is_regex: bool = False
    _compiled: re.Pattern[str] | None = field(default=None, repr=False, compare=False)

    def apply(self, text: str) -> str:
        if self.is_regex:
            if self._compiled is None:
                return text
            return self._compiled.sub(self.replacement, text)
        return text.replace(self.pattern, self.replacement)

    @staticmethod
    def parse(left: str, right: str) -> "ReplaceRule":
        if left.startswith(_RE_PREFIX):
            regex_str = left[len(_RE_PREFIX):]
            try:
                compiled = re.compile(regex_str)
            except re.error as e:
                logger.warning("無効な正規表現をスキップ: %s (%s)", regex_str, e)
                return ReplaceRule(pattern=regex_str, replacement=right, is_regex=True, _compiled=None)
            return ReplaceRule(pattern=regex_str, replacement=right, is_regex=True, _compiled=compiled)
        return ReplaceRule(pattern=left, replacement=right)


@dataclass
class FilterConfig:
    exclude_speaker_rules: list[MatchRule] = field(
        default_factory=lambda: [MatchRule.parse(p) for p in _DEFAULT_EXCLUDE_SPEAKER],
    )
    exclude_patterns: list[MatchRule] = field(
        default_factory=lambda: [MatchRule.parse(p) for p in _DEFAULT_EXCLUDE_PATTERNS],
    )
    replace_rules: list[ReplaceRule] = field(default_factory=list)

    @staticmethod
    def load(path: Path) -> "FilterConfig":
        if not path.exists():
            return FilterConfig()

        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("フィルタ設定の読み込みに失敗: %s", path)
            return FilterConfig()

        exclude_speaker_rules: list[MatchRule] = []
        exclude_patterns: list[MatchRule] = []
        replace_rules: list[ReplaceRule] = []
        section: str | None = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped[1:-1].lower()
                continue

            if section == "exclude_speaker":
                exclude_speaker_rules.append(MatchRule.parse(stripped))
            elif section == "exclude":
                exclude_patterns.append(MatchRule.parse(stripped))
            elif section == "replace":
                if "=>" in stripped:
                    left, _, right = stripped.partition("=>")
                    replace_rules.append(ReplaceRule.parse(left.strip(), right.strip()))

        return FilterConfig(
            exclude_speaker_rules=exclude_speaker_rules,
            exclude_patterns=exclude_patterns,
            replace_rules=replace_rules,
        )

    @staticmethod
    def save_default(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DEFAULT_FILTERS_CONTENT, encoding="utf-8")

    def should_exclude_speaker(self, speaker: str) -> bool:
        return any(rule.matches(speaker) for rule in self.exclude_speaker_rules)

    def should_exclude_body(self, body: str) -> bool:
        return any(rule.matches(body) for rule in self.exclude_patterns)

    def apply_replacements(self, text: str) -> str:
        for rule in self.replace_rules:
            text = rule.apply(text)
        return text
