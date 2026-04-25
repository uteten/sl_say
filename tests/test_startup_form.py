import pytest

try:
    import tkinter  # noqa: F401
    HAS_TKINTER = True
except (ImportError, ModuleNotFoundError):
    HAS_TKINTER = False

pytestmark = pytest.mark.skipif(not HAS_TKINTER, reason="tkinter not available")


class TestFormResult:
    def test_stores_values(self) -> None:
        from app.startup_form import FormResult

        result = FormResult(file_path="C:\\test\\chat.txt", rate="+50%", volume=80)
        assert result.file_path == "C:\\test\\chat.txt"
        assert result.rate == "+50%"
        assert result.volume == 80

    def test_default_rate_format(self) -> None:
        from app.startup_form import FormResult

        result = FormResult(file_path="path", rate="+0%", volume=100)
        assert result.rate == "+0%"


class TestStartupFormInit:
    def test_initial_values_stored(self) -> None:
        from app.startup_form import StartupForm

        form = StartupForm(initial_file="C:\\test.txt", initial_rate="-20%")
        assert form._initial_file == "C:\\test.txt"
        assert form._initial_rate == "-20%"
        assert form._result is None
