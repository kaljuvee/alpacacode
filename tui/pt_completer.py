"""prompt_toolkit completer for the Rich CLI — provides dropdown completion."""

from prompt_toolkit.completion import Completer, Completion
from tui.completer import COMMANDS


class PTCommandCompleter(Completer):
    """Dropdown completer for commands and key:value parameters."""

    def get_completions(self, document, complete_event):
        line = document.text_before_cursor.lstrip("/")
        word = document.get_word_before_cursor(WORD=True)

        # Strip "/" from the word being completed
        stripped_word = word.lstrip("/")

        parts = line.split()

        # Case 1: Completing command name (first word)
        if not parts or (len(parts) == 1 and not line.endswith(" ")):
            for cmd, param_defs in sorted(COMMANDS.items()):
                if cmd.startswith(stripped_word):
                    desc = self._cmd_description(cmd)
                    yield Completion(cmd, start_position=-len(stripped_word),
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

    @staticmethod
    def _cmd_description(cmd):
        descs = {
            "help": "show help",
            "status": "system status",
            "trades": "show trades from DB",
            "runs": "show runs from DB",
            "clear": "clear screen",
            "exit": "quit",
            "agent:backtest": "run parameterized backtest",
            "agent:validate": "validate a run",
            "agent:paper": "paper trade in background",
            "agent:full": "backtest → validate → paper → validate",
            "agent:reconcile": "DB vs Alpaca reconciliation",
            "agent:status": "agent states",
            "agent:runs": "query runs",
            "agent:trades": "query trades",
            "agent:stop": "stop running agent",
            "alpaca:backtest": "Alpaca-style backtest",
        }
        return descs.get(cmd, "")
