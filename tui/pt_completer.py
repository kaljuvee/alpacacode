"""prompt_toolkit completer for the Rich CLI — provides dropdown completion."""

from prompt_toolkit.completion import Completer, Completion
from tui.completer import COMMANDS

# Command templates with typical default values.
# Each entry: (full_command_string, description)
TEMPLATES = [
    ("agent:backtest lookback:1m",                        "1-month backtest"),
    ("agent:backtest lookback:3m",                        "3-month backtest"),
    ("agent:backtest lookback:6m",                        "6-month backtest"),
    ("agent:backtest lookback:1m hours:extended",          "1-month extended hours"),
    ("agent:backtest lookback:1m intraday_exit:true",      "1-month with intraday exits"),
    ("agent:backtest lookback:1m pdt:false",               "1-month no PDT rule"),
    ("agent:paper duration:1d",                            "paper trade 1 day"),
    ("agent:paper duration:7d",                            "paper trade 7 days"),
    ("agent:paper duration:30d",                           "paper trade 30 days"),
    ("agent:paper duration:7d hours:extended",             "paper trade 7d extended hours"),
    ("agent:paper duration:7d email:false",                "paper trade 7d no emails"),
    ("agent:full lookback:1m duration:7d",                 "full cycle 1m backtest + 7d paper"),
    ("agent:full lookback:3m duration:7d",                 "full cycle 3m backtest + 7d paper"),
    ("agent:full lookback:1m duration:7d hours:extended",  "full cycle extended hours"),
    ("agent:validate source:backtest",                     "validate backtest run"),
    ("agent:validate source:paper_trade",                  "validate paper trades"),
    ("agent:reconcile window:7d",                          "reconcile last 7 days"),
    ("agent:reconcile window:14d",                         "reconcile last 14 days"),
    ("agent:reconcile window:30d",                         "reconcile last 30 days"),
    ("agent:status",                                       "agent states"),
    ("agent:runs",                                         "query runs"),
    ("agent:stop",                                         "stop running agent"),
    ("trades",                                             "show trades from DB"),
    ("runs",                                               "show runs from DB"),
    ("help",                                               "show help"),
]


class PTCommandCompleter(Completer):
    """Dropdown completer for commands and key:value parameters."""

    def get_completions(self, document, complete_event):
        line = document.text_before_cursor.lstrip("/")
        word = document.get_word_before_cursor(WORD=True)

        # Strip "/" from the word being completed
        stripped_word = word.lstrip("/")

        parts = line.split()

        # Case 1: Completing command name (first word) — show templates
        if not parts or (len(parts) == 1 and not line.endswith(" ")):
            for template, desc in TEMPLATES:
                if template.startswith(stripped_word):
                    yield Completion(template, start_position=-len(stripped_word),
                                     display_meta=desc)
            return

        # Case 2: Command known, completing parameters
        cmd = parts[0].lower()
        if cmd not in COMMANDS:
            return
        param_defs = COMMANDS[cmd]
        if not param_defs:
            return

        # Which param keys are already used?
        used = {p.partition(":")[0].lower() for p in parts[1:] if ":" in p}

        # Case 2a: word contains ":" → completing a value
        if ":" in word:
            key, _, partial = word.partition(":")
            values = param_defs.get(key.lower())
            if values:
                for v in values:
                    if v.startswith(partial):
                        yield Completion(f"{key}:{v}", start_position=-len(word))
            return

        # Case 2b: completing a param key
        for k in sorted(param_defs):
            if k.startswith(word) and k not in used:
                values = param_defs[k]
                meta = ", ".join(values) if values else "free-form"
                yield Completion(f"{k}:", start_position=-len(word),
                                 display_meta=meta)
