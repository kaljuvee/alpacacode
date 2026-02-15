"""FastHTML web shell for AlpacaCode — browser-based CLI."""
import os
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from dotenv import load_dotenv
from fasthtml.common import *
from tui.command_processor import CommandProcessor
from tui.strategy_cli import StrategyCLI

load_dotenv()

# Singleton state container (persists across requests)
cli = StrategyCLI()

# ---------------------------------------------------------------------------
# Google OAuth setup (optional — gracefully skip if no creds)
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
_oauth_enabled = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

if _oauth_enabled:
    from fasthtml.oauth import GoogleAppClient, redir_url

FREE_QUERY_LIMIT = 5
# Commands that don't count toward the free query limit
_FREE_COMMANDS = {"help", "h", "?", "clear", "cls", "exit", "quit", "q", "status"}

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

/* Nav bar */
nav.top-nav { display: flex; align-items: center; justify-content: space-between;
              padding: 0.5rem 0; margin-bottom: 0.5rem;
              border-bottom: 1px solid var(--pico-muted-border-color); }
nav.top-nav .nav-brand { font-weight: bold; font-size: 1.1em; color: var(--pico-primary); text-decoration: none; }
nav.top-nav .nav-links { display: flex; gap: 1rem; align-items: center; font-size: 0.85em; }
nav.top-nav .nav-links a { color: var(--pico-muted-color); text-decoration: none; }
nav.top-nav .nav-links a:hover { color: var(--pico-primary); }

/* Query badge */
.query-badge { font-size: 0.75em; color: var(--pico-muted-color);
               background: var(--pico-card-background-color); padding: 0.15rem 0.5rem;
               border-radius: 0.25rem; border: 1px solid var(--pico-muted-border-color); }

/* Sign-in prompt */
.signin-card { text-align: center; padding: 2rem; margin: 1rem 0;
               border: 1px solid var(--pico-muted-border-color); border-radius: 0.5rem;
               background: var(--pico-card-background-color); }
.signin-card h4 { margin-bottom: 0.5rem; }
.signin-card p { color: var(--pico-muted-color); margin-bottom: 1rem; }
.signin-card a { display: inline-block; padding: 0.5rem 1.5rem;
                 background: var(--pico-primary); color: #fff; border-radius: 0.25rem;
                 text-decoration: none; font-weight: 600; }

/* Screenshot gallery */
.screenshot-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1rem; }
@media (max-width: 768px) { .screenshot-grid { grid-template-columns: 1fr; } }
.screenshot-grid figure { margin: 0; }
.screenshot-grid img { width: 100%; border-radius: 0.5rem; border: 1px solid var(--pico-muted-border-color); }
.screenshot-grid figcaption { color: var(--pico-muted-color); font-size: 0.85em; margin-top: 0.3rem; text-align: center; }

/* Download page */
.dl-page { max-width: 700px; margin: 0 auto; }
.dl-page pre { position: relative; }
.copy-btn { position: absolute; top: 0.5rem; right: 0.5rem; background: var(--pico-primary);
            color: #fff; border: none; padding: 0.25rem 0.75rem; border-radius: 0.25rem;
            cursor: pointer; font-size: 0.8em; }
.copy-btn:hover { opacity: 0.85; }
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

    # Column 3: Research & Options
    col3 = Div(
        *_section("Research", [
            ("news TSLA", "company news"),
            ("  provider:xai|tavily", "force news provider"),
            ("profile TSLA", "company profile"),
            ("financials AAPL", "income & balance sheet"),
            ("price TSLA", "quote & technicals"),
            ("movers", "top gainers & losers"),
            ("analysts AAPL", "ratings & targets"),
            ("valuation AAPL,MSFT", "valuation comparison"),
        ]),
        *_section("Options", [
            ("hours:extended", "4AM-8PM ET"),
            ("intraday_exit:true", "5-min bar exits"),
            ("pdt:false", "disable PDT (>$25k)"),
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
# Nav bar helper
# ---------------------------------------------------------------------------

def _nav(session):
    """Build the top navigation bar."""
    user = session.get("user") if session else None
    links = [
        A("Download", href="/download"),
        A("Screenshots", href="/screenshots"),
    ]
    if user:
        links.append(Span(user.get("email", "user"), style="color: var(--pico-color);"))
        links.append(A("Logout", href="/logout"))
    elif _oauth_enabled:
        links.append(A("Sign in", href="/login"))
    return Nav(
        A("AlpacaCode", href="/", cls="nav-brand"),
        Div(*links, cls="nav-links"),
        cls="top-nav",
    )


def _query_badge(session):
    """Show remaining free queries for anonymous users."""
    user = session.get("user") if session else None
    if user:
        return ""
    count = session.get("query_count", 0) if session else 0
    remaining = max(0, FREE_QUERY_LIMIT - count)
    return Span(f"{remaining} free queries remaining", cls="query-badge")


def _signin_prompt():
    """Card shown when free query limit is reached."""
    parts = [
        H4("Free query limit reached"),
        P(f"You've used all {FREE_QUERY_LIMIT} free queries."),
    ]
    if _oauth_enabled:
        parts.append(P("Sign in with Google for unlimited access."))
        parts.append(A("Sign in with Google", href="/login"))
    else:
        parts.append(P("Authentication is not configured on this instance."))
    return Div(*parts, cls="signin-card")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@rt("/")
def get(session):
    return (
        Title("AlpacaCode"),
        Main(
            _nav(session),
            Div(
                _query_badge(session),
                style="text-align: right; margin-bottom: 0.5rem;",
            ),
            Div(_help_html(), id="output"),
            Form(
                Input(type="text", name="command",
                      placeholder="Type a command...",
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
async def post(command: str, session):
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
        # Rate-limit check for anonymous users
        user = session.get("user")
        if not user:
            # Only count non-free commands
            first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
            if first_word not in _FREE_COMMANDS:
                count = session.get("query_count", 0)
                if count >= FREE_QUERY_LIMIT:
                    return Div(
                        P(B(f"> {command}"), cls="cmd-echo"),
                        _signin_prompt(),
                        cls="cmd-entry",
                    )
                session["query_count"] = count + 1

        processor = CommandProcessor(cli)
        result_md = await processor.process_command(command) or ""

    return Div(
        P(B(f"> {command}"), cls="cmd-echo"),
        Div(result_md, cls="marked"),
        cls="cmd-entry",
    )


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------

if _oauth_enabled:
    @rt("/login")
    def login_get(request):
        client = GoogleAppClient(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        redirect_uri = redir_url(request, "/auth/callback")
        login_url = client.login_link(redirect_uri)
        return RedirectResponse(login_url)

    @rt("/auth/callback")
    async def auth_callback(request, session, code: str = "", error: str = ""):
        if error or not code:
            return RedirectResponse("/")
        # Create a fresh client per request (thread safety — retr_info stores token on instance)
        client = GoogleAppClient(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        redirect_uri = redir_url(request, "/auth/callback")
        info = await client.retr_info_async(code, redirect_uri)
        session["user"] = {"email": info.get("email", ""), "name": info.get("name", "")}
        session["query_count"] = 0
        return RedirectResponse("/")

    @rt("/logout")
    def logout_get(session):
        session.pop("user", None)
        session["query_count"] = 0
        return RedirectResponse("/")
else:
    # Stub routes when OAuth is not configured
    @rt("/login")
    def login_get():
        return RedirectResponse("/")

    @rt("/logout")
    def logout_get(session):
        session.pop("user", None)
        session["query_count"] = 0
        return RedirectResponse("/")


# ---------------------------------------------------------------------------
# Download page
# ---------------------------------------------------------------------------

@rt("/download")
def download_get(session):
    curl_cmd = "curl -fsSL https://alpacacode.com/install.sh | bash"
    return (
        Title("Download — AlpacaCode"),
        Main(
            _nav(session),
            Div(
                H2("Install AlpacaCode"),
                P("One-line install (requires Python 3.13+):", style="color: var(--pico-muted-color);"),
                Div(
                    Pre(Code(curl_cmd), id="curl-cmd"),
                    Button("Copy", cls="copy-btn", onclick="navigator.clipboard.writeText(document.getElementById('curl-cmd').textContent)"),
                    style="position: relative;",
                ),
                Hr(),
                H4("Manual install"),
                Div("""
```bash
git clone https://github.com/kaljuvee/alpacacode.git ~/.alpacacode
cd ~/.alpacacode
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit with your API keys
python alpaca_code.py
```
""", cls="marked"),
                Hr(),
                H4("Requirements"),
                Ul(
                    Li("Python 3.13+"),
                    Li("PostgreSQL (for trade history)"),
                    Li("Alpaca paper trading account"),
                    Li("Massive (Polygon) API key for market data"),
                ),
                cls="dl-page",
            ),
        ),
    )


@rt("/install.sh")
def install_script_get():
    script_path = Path(__file__).parent / "install.sh"
    if script_path.exists():
        content = script_path.read_text()
    else:
        content = "#!/bin/bash\necho 'install.sh not found on server'\nexit 1\n"
    return Response(content, media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=install.sh"})


# ---------------------------------------------------------------------------
# Screenshots page
# ---------------------------------------------------------------------------

# Screenshots: (filename, caption)
_SCREENSHOTS = [
    ("help.png", "Command reference — default landing view"),
    ("news.png", "News command — company headlines"),
    ("trades.png", "Trades table — executed trades from DB"),
    ("backtest.png", "Backtest results — strategy performance"),
]


@rt("/screenshots")
def screenshots_get(session):
    static_dir = Path(__file__).parent / "static"
    figures = []
    for fname, caption in _SCREENSHOTS:
        if (static_dir / fname).exists():
            figures.append(
                Figure(
                    Img(src=f"/static/{fname}", alt=caption, loading="lazy"),
                    Figcaption(caption),
                )
            )
    if not figures:
        figures.append(P("No screenshots available yet.", style="color: var(--pico-muted-color);"))
    return (
        Title("Screenshots — AlpacaCode"),
        Main(
            _nav(session),
            H2("Screenshots"),
            Div(*figures, cls="screenshot-grid") if len(figures) > 1 or (figures and figures[0].tag == "figure") else Div(*figures),
        ),
    )


serve(port=5002)
