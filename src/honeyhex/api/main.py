from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import uvicorn
    except ImportError:
        sys.stderr.write(
            "honeyhex-api requires registry extras: "
            "pip install 'honeyhex[registry]'\n",
        )
        raise SystemExit(1) from None

    host = os.environ.get("HONEYHEX_REGISTRY_HOST", "127.0.0.1")
    port = int(os.environ.get("HONEYHEX_REGISTRY_PORT", "8765"))
    uvicorn.run("honeyhex.api.app:app", host=host, port=port, factory=False)


if __name__ == "__main__":
    main()
