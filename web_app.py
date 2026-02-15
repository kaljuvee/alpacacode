"""FastHTML web shell for AlpacaCode — browser-based CLI."""
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from fasthtml.common import *
from tui.command_processor import CommandProcessor
from tui.strategy_cli import StrategyCLI

# Singleton state container (persists across requests)
cli = StrategyCLI()

# ---------------------------------------------------------------------------
# Custom CSS & JS
# ---------------------------------------------------------------------------

_theme = Script("document.documentElement.dataset.theme='dark';")

_css = Style("""
body { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; }
main { max-width: 960px; margin: 0 auto; padding: 1rem; display: flex; flex-direction: column; height: 95vh; }
#output { flex: 1; overflow-y: auto; }
.cmd-entry { border-bottom: 1px solid var(--pico-muted-border-color); padding: 0.75rem 0; }
.cmd-echo { color: var(--pico-muted-color); font-size: 0.85em; margin-bottom: 0.25rem; }
.cmd-echo b { color: var(--pico-primary); }
#cmd-form { display: flex; gap: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--pico-muted-border-color); }
#cmd-form input { flex: 1; margin-bottom: 0; }
#cmd-form button { width: auto; margin-bottom: 0; }
.help-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; font-size: 0.85em; }
@media (max-width: 768px) { .help-grid { grid-template-columns: 1fr; } }
.help-grid h4 { color: var(--pico-primary); margin: 0.8rem 0 0.3rem; font-size: 0.95em; }
.help-grid h4:first-child { margin-top: 0; }
.help-grid dl { margin: 0; }
.help-grid dt { color: #e2c07b; font-size: 0.9em; margin-top: 0.3rem; }
.help-grid dd { color: var(--pico-muted-color); margin: 0 0 0 0.5rem; font-size: 0.85em; }
.htmx-request .htmx-indicator { display: inline; }
.htmx-indicator { display: none; }
""")

_js = Script("""
document.addEventListener('htmx:afterSettle', function() {
    var out = document.getElementById('output');
    if (out) out.scrollTop = out.scrollHeight;
});
document.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.elt && evt.detail.elt.id === 'cmd-form') {
        evt.detail.elt.reset();
        evt.detail.elt.querySelector('input').focus();
    }
});
// Extend HTMX timeout for long-running commands (backtests)
document.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.timeout = 300000;  // 5 minutes
});
""")

app, rt = fast_app(hdrs=[_theme, MarkdownJS(), _css, _js])

# ---------------------------------------------------------------------------
# Help — 3-column HTML grid (mirrors Rich CLI help layout)
# ---------------------------------------------------------------------------


def _help_html():
    """Return a 3-column help grid as FastHTML components."""

    def _section(title, items):
        """Build an h4 + dl for a help section."""
        dl_items = []
        for cmd, desc in items:
            dl_items.append(Dt(cmd))
            dl_items.append(Dd(desc))
        return (H4(title), Dl(*dl_items))

    # Column 1: Backtest, Validate, Reconcile
    col1 = Div(
        *_section("Backtest", [
            ("agent:backtest lookback:1m", "1-month backtest"),
            ("  symbols:AAPL,TSLA", "custom symbols"),
            ("  hours:extended", "pre/after-market"),
            ("  intraday_exit:true", "5-min TP/SL bars"),
            ("  pdt:false", "disable PDT rule"),
        ]),
        *_section("Validate", [
            ("agent:validate run-id:<uuid>", "validate a run"),
            ("  source:paper_trade", "validate paper trades"),
        ]),
        *_section("Reconcile", [
            ("agent:reconcile", "DB vs Alpaca (7d)"),
            ("  window:14d", "custom window"),
        ]),
    )

    # Column 2: Paper Trade, Full Cycle, Query & Monitor
    col2 = Div(
        *_section("Paper Trade", [
            ("agent:paper duration:7d", "run in background"),
            ("  symbols:AAPL,MSFT poll:60", "custom config"),
            ("  hours:extended", "extended hours"),
            ("  email:false", "disable email reports"),
            ("  pdt:false", "disable PDT rule"),
        ]),
        *_section("Full Cycle", [
            ("agent:full lookback:1m duration:1m", "BT > Val > PT > Val"),
            ("  hours:extended", "extended hours"),
        ]),
        *_section("Query & Monitor", [
            ("trades / runs", "DB tables"),
            ("agent:report", "performance summary"),
            ("  type:backtest run-id:<uuid>", "filter / detail"),
            ("agent:status", "agent states"),
            ("agent:stop", "stop background task"),
        ]),
    )

    # Column 3: Options & Parameters
    col3 = Div(
        *_section("Options", [
            ("hours:regular", "9:30AM-4PM ET (default)"),
            ("hours:extended", "4AM-8PM ET"),
            ("intraday_exit:true", "5-min bar exits"),
            ("pdt:false", "disable PDT (>$25k)"),
            ("email:false", "no daily P&L emails"),
        ]),
        *_section("Parameters", [
            ("lookback:1m|3m|6m|1y", "backtest period"),
            ("strategy:buy_the_dip", "strategy name"),
            ("symbols:AAPL,TSLA", "comma-separated"),
            ("capital:10000", "initial capital"),
        ]),
        *_section("General", [
            ("help / status / clear", ""),
        ]),
    )

    return Div(
        H3("AlpacaCode — Command Reference"),
        Div(col1, col2, col3, cls="help-grid"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@rt("/")
def get():
    return (
        Title("AlpacaCode"),
        Main(
            H3("AlpacaCode"),
            Div(id="output"),
            Form(
                Input(type="text", name="command",
                      placeholder="Type a command... (try 'help')",
                      autofocus=True, autocomplete="off"),
                Button("Run", type="submit"),
                Span(" Running...", cls="htmx-indicator",
                     style="color: var(--pico-muted-color); font-size: 0.85em;"),
                id="cmd-form",
                hx_post="/cmd", hx_target="#output", hx_swap="beforeend",
                hx_indicator=".htmx-indicator",
            ),
        ),
    )


@rt("/cmd")
async def post(command: str):
    cmd_lower = command.strip().lower()

    if not command.strip():
        return ""

    # Special web-only handling
    if cmd_lower in ("exit", "quit", "q"):
        result_md = "Close the browser tab to end this session."
    elif cmd_lower in ("clear", "cls"):
        return Div(id="output", hx_swap_oob="innerHTML")
    elif cmd_lower in ("help", "h", "?"):
        return Div(
            P(B(f"> {command}"), cls="cmd-echo"),
            _help_html(),
            cls="cmd-entry",
        )
    else:
        processor = CommandProcessor(cli)
        result_md = await processor.process_command(command) or ""

    return Div(
        P(B(f"> {command}"), cls="cmd-echo"),
        Div(result_md, cls="marked"),
        cls="cmd-entry",
    )


serve(port=5002)
