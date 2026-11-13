"""python -m poc.run [--port 4000]. Ctrl-C stops this stack only."""
import argparse
from datetime import datetime
from pathlib import Path
import signal
import time

from poc.runtime import ROOT, Stack


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4000)
    args = parser.parse_args()
    directory = ROOT / 'poc/.runtime' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    stack = Stack(directory, args.port)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        print('Starting temporary PostgreSQL, synthetic providers and native LiteLLM...', flush=True)
        stack.start()
        print(f'API: {stack.url}/v1\nAdmin UI: {stack.url}/ui\nDocs: {stack.url}/docs', flush=True)
        print(f'Local credentials (0600): {directory / "credentials.json"}', flush=True)
        print('Ctrl-C stops the stack. Synthetic data stays in this ignored run directory.', flush=True)
        while True:
            if stack.proxy.poll() is not None or stack.upstream.poll() is not None:
                raise RuntimeError('A POC service exited; inspect local logs.')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopping POC...')
    finally:
        stack.close()


if __name__ == '__main__':
    main()
