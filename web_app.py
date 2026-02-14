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
""")

app, rt = fast_app(hdrs=[_theme, MarkdownJS(), _css, _js])

# ---------------------------------------------------------------------------
# Static help (Rich help prints to console — not useful for web)
# ---------------------------------------------------------------------------

HELP_MD = """\
# AlpacaCode — Command Reference

## Backtest
| Command | Description |
|---------|-------------|
| `agent:backtest lookback:1m` | Run a 1-month backtest |
| `  symbols:AAPL,TSLA` | Custom symbols |
| `  hours:extended` | Pre/after-market (4AM-8PM ET) |
| `  intraday_exit:true` | 5-min bar TP/SL exits |
| `  pdt:false` | Disable PDT rule (>$25k) |

## Validate & Reconcile
| Command | Description |
|---------|-------------|
| `agent:validate run-id:<id>` | Validate a backtest run |
| `  source:paper_trade` | Validate paper trades instead |
| `agent:reconcile window:14d` | DB vs Alpaca reconciliation |

## Paper Trade
| Command | Description |
|---------|-------------|
| `agent:paper duration:7d` | Paper trade in background |
| `  symbols:AAPL,MSFT poll:60` | Custom config |
| `  hours:extended` | Extended hours |
| `  email:false` | Disable daily P&L emails |
| `  pdt:false` | Disable PDT rule |

## Full Cycle (Backtest > Validate > Paper > Validate)
| Command | Description |
|---------|-------------|
| `agent:full lookback:1m duration:1m` | Run full cycle |

## Query & Monitor
| Command | Description |
|---------|-------------|
| `trades` | Show trades from DB |
| `runs` | Show runs from DB |
| `agent:status` | Show agent states |
| `agent:stop` | Stop background task |
| `status` | Show current config |
| `clear` | Clear output |
"""

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
                id="cmd-form",
                hx_post="/cmd", hx_target="#output", hx_swap="beforeend",
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
        result_md = HELP_MD
    else:
        processor = CommandProcessor(cli)
        result_md = await processor.process_command(command) or ""

    return Div(
        P(B(f"> {command}"), cls="cmd-echo"),
        Div(result_md, cls="marked"),
        cls="cmd-entry",
    )


serve(port=5002)
