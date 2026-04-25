import argparse
import logging
import signal
import sys
from typing import Sequence

from app.audio_player import AudioPlayer
from app.chat_parser import ChatParser
from app.file_watcher import FileWatcher
from app.filter_config import FilterConfig
from app.path_resolver import PathResolver
from app.tts_engine import TTSEngine
from app.tts_queue import TTSQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Firestorm chat.txt を監視し、新規メッセージを音声で読み上げる",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="監視対象の chat.txt パス（省略時はFirestormデフォルトパス）",
    )
    parser.add_argument(
        "--voice",
        default="ja-JP-NanamiNeural",
        help="TTS音声名（デフォルト: ja-JP-NanamiNeural）",
    )
    parser.add_argument(
        "--rate",
        default="+0%",
        help="読み上げ速度（例: +50%%, -20%%、デフォルト: +0%%）",
    )
    return parser.parse_args(argv)


def needs_gui(args: argparse.Namespace) -> bool:
    """CLI引数でファイルパスが指定されていない場合はGUIが必要."""
    return args.file is None


def build_pipeline(
    file_path: str,
    engine: TTSEngine,
    player: AudioPlayer,
    filter_config: FilterConfig | None = None,
) -> tuple[FileWatcher, TTSQueue]:
    watcher = FileWatcher(file_path)
    tts_queue = TTSQueue(engine, player, filter_config=filter_config)
    return watcher, tts_queue


def main() -> None:
    args = parse_args()

    from app.config_store import ConfigStore

    store = ConfigStore()
    filters_path = store._config_dir / "filters.txt"
    if not filters_path.exists():
        FilterConfig.save_default(filters_path)
        logger.info("デフォルトフィルタ設定を作成: %s", filters_path)

    if needs_gui(args):
        from app.config_store import AppConfig
        from app.startup_form import FormResult, StartupForm

        config = store.load()
        active_watcher: list[FileWatcher] = []
        active_queue: list[TTSQueue] = []
        active_engine: list[TTSEngine] = []
        active_player: list[AudioPlayer] = []

        def on_start(result: FormResult) -> None:
            store.save(AppConfig(file_path=result.file_path, rate=result.rate, volume=result.volume))
            import threading

            _stop_active()

            t = threading.Thread(
                target=_run_pipeline_gui,
                args=(result.file_path, args.voice, result.rate, result.volume, filters_path,
                      active_watcher, active_queue, active_engine, active_player),
                daemon=True,
            )
            t.start()

        def on_stop() -> None:
            _stop_active()

        def on_rate_change(rate: str) -> None:
            for e in active_engine:
                e.rate = rate

        def on_volume_change(volume: int) -> None:
            for p in active_player:
                p._volume = max(0, min(100, volume))

        def _stop_active() -> None:
            for w in active_watcher:
                w.stop()
            active_watcher.clear()
            for q in active_queue:
                q.stop()
            active_queue.clear()
            active_engine.clear()
            active_player.clear()

        form = StartupForm(
            initial_file=config.file_path,
            initial_rate=config.rate,
            initial_volume=config.volume,
            filters_path=filters_path,
            on_start=on_start,
            on_stop=on_stop,
            on_rate_change=on_rate_change,
            on_volume_change=on_volume_change,
        )
        form.show()
        _stop_active()
        sys.exit(0)
    else:
        _run_pipeline(args.file, args.voice, args.rate, 100, filters_path)


def _run_pipeline_gui(
    file_path_arg: str,
    voice: str,
    rate: str,
    volume: int,
    filters_path: str,
    active_watcher: list,
    active_queue: list,
    active_engine: list,
    active_player: list,
) -> None:
    resolver = PathResolver()
    try:
        file_path = resolver.resolve(file_path_arg)
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    filter_config = FilterConfig.load(filters_path)

    engine = TTSEngine(voice=voice, rate=rate)
    player = AudioPlayer(volume=volume)
    watcher, tts_queue = build_pipeline(file_path, engine, player, filter_config=filter_config)

    active_watcher.append(watcher)
    active_queue.append(tts_queue)
    active_engine.append(engine)
    active_player.append(player)

    parser = ChatParser(filter_config=filter_config)
    tts_queue.start()

    watcher.preview(5)
    logger.info("監視開始: %s", file_path)
    try:
        for line in watcher.watch():
            msg = parser.parse_line(line)
            if msg and msg.skipped:
                logger.info("%s: %s (skip)", msg.speaker, msg.body)
            elif msg:
                logger.info("%s: %s", msg.speaker, msg.body)
                tts_queue.enqueue(msg)
            else:
                logger.info("(未パース) %s", line[:80])
    except Exception:
        logger.exception("監視ループエラー")
    finally:
        watcher.stop()
        tts_queue.stop()
        if watcher in active_watcher:
            active_watcher.remove(watcher)
        if tts_queue in active_queue:
            active_queue.remove(tts_queue)
        if engine in active_engine:
            active_engine.remove(engine)
        if player in active_player:
            active_player.remove(player)
    logger.info("監視停止")


def _run_pipeline(
    file_path_arg: str,
    voice: str,
    rate: str,
    volume: int,
    filters_path: str,
    install_signal_handler: bool = True,
) -> None:
    resolver = PathResolver()
    try:
        file_path = resolver.resolve(file_path_arg)
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    filter_config = FilterConfig.load(filters_path)

    engine = TTSEngine(voice=voice, rate=rate)
    player = AudioPlayer(volume=volume)
    watcher, tts_queue = build_pipeline(file_path, engine, player, filter_config=filter_config)

    parser = ChatParser(filter_config=filter_config)
    tts_queue.start()

    if install_signal_handler:
        def shutdown(signum: int, frame: object) -> None:
            logger.info("終了中...")
            watcher.stop()
            tts_queue.stop()
        signal.signal(signal.SIGINT, shutdown)

    watcher.preview(5)
    logger.info("監視開始: %s", file_path)
    try:
        for line in watcher.watch():
            msg = parser.parse_line(line)
            if msg and msg.skipped:
                logger.info("%s: %s (skip)", msg.speaker, msg.body)
            elif msg:
                logger.info("%s: %s", msg.speaker, msg.body)
                tts_queue.enqueue(msg)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        tts_queue.stop()


if __name__ == "__main__":
    main()
