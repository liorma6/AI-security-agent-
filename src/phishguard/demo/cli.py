"""Launch only the local demo; no public-host or remote-model options."""

import json


def register(commands):
    command = commands.add_parser("demo", help="Start the local pasted-email Gradio demo")
    command.add_argument("--port", type=int, default=7860)


def run(args):
    if not 1024 <= args.port <= 65535:
        print(json.dumps({"error": "port_must_be_between_1024_and_65535"}))
        return 2
    try:
        from phishguard.demo.ui import launch

        launch(args.port)
    except KeyboardInterrupt:
        return 0
    except (ImportError, OSError, RuntimeError, ValueError):
        print(json.dumps({"error": "demo_unavailable_check_demo_extra_and_free_port"}))
        return 2
    return 0
