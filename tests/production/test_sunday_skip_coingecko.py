from pathlib import Path

from crypto_platform.platform import Module1Runner


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "crypto-production-cycle.yml"
ORCHESTRATOR = ROOT / "crypto_platform" / "production" / "orchestrator.py"


class _Log:
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(message % args if args else message)


class _ForbiddenCoinGecko:
    def healthcheck(self):
        raise AssertionError("CoinGecko must not be called in Sunday skip mode")


def test_sunday_schedule_requests_full_refresh_without_coingecko():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "45 10 * * 0"' in text
    assert "CRYPTO_SKIP_COINGECKO_REQUESTED:" in text
    assert "github.event.schedule == '45 10 * * 0'" in text
    assert 'EXTRA_ARGS="$EXTRA_ARGS --skip-coingecko"' in text


def test_full_refresh_manual_or_sunday_skips_coingecko():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert (
        "CRYPTO_SKIP_COINGECKO_REQUESTED: "
        "${{ (github.event_name == 'schedule' && github.event.schedule == '45 10 * * 0') || "
        "(github.event_name == 'workflow_dispatch' && inputs.full_refresh == true) }}"
    ) in text


def test_normal_manual_refresh_does_not_force_skip_coingecko():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "inputs.full_refresh == true" in text
    assert "inputs.full_refresh == false" not in text


def test_module1_skip_mode_makes_no_coingecko_request():
    runner = object.__new__(Module1Runner)
    runner.skip_coingecko = True
    runner.log = _Log()
    runner.coin_gecko = _ForbiddenCoinGecko()

    assert runner.run_market() is None
    assert runner.log.messages == ["CoinGecko collection skipped by governed refresh mode."]


def test_orchestrator_propagates_skip_coingecko_only_to_module1():
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "skip_coingecko: bool = False" in text
    assert "if spec.number == 1 and self.options.skip_coingecko:" in text
    assert 'command.append("--skip-coingecko")' in text
