"""Own only the processes and disposable PostgreSQL cluster created by this POC."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time

import httpx
import pgserver

ROOT = Path(__file__).resolve().parents[1]


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Stack:
    def __init__(self, directory: Path, port: int = 0):
        self.directory = directory.resolve()
        self.port = port or unused_port()
        self.upstream_port = unused_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self.master = 'sk-' + secrets.token_hex(24)
        self.stats_key = secrets.token_hex(24)
        self.upstream_key = secrets.token_hex(24)
        self.ui_password = secrets.token_urlsafe(24)
        self.pg = None
        self.proxy = None
        self.upstream = None
        self.handles = []
        self.env = os.environ.copy()
        # Inherit trust/proxy settings; local HTTP must remain local.
        no_proxy = self.env.get('NO_PROXY', self.env.get('no_proxy', ''))
        self.env['NO_PROXY'] = self.env['no_proxy'] = no_proxy + ',localhost,127.0.0.1'
        self.env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + self.env.get('PATH', '')
        self.env['PYTHONPATH'] = str(ROOT) + os.pathsep + self.env.get('PYTHONPATH', '')

    def spawn(self, args: list[str], name: str):
        handle = (self.directory / f'{name}.log').open('ab')
        self.handles.append(handle)
        return subprocess.Popen(args, cwd=ROOT, env=self.env, stdout=handle,
                                stderr=subprocess.STDOUT, start_new_session=True)

    @staticmethod
    def stop_process(process):
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)

    def wait_ready(self, url, process, timeout=180):
        deadline = time.monotonic() + timeout
        with httpx.Client(trust_env=False, timeout=2) as client:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f'POC process exited ({process.returncode}); inspect local logs in {self.directory}')
                try:
                    if client.get(url).status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.3)
        raise TimeoutError(f'POC did not become ready; inspect {self.directory}')

    def start(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        try:
            # Use bundled real PostgreSQL binaries; require password auth on loopback TCP.
            # LiteLLM's migration helper strips Unix-socket URI query parameters.
            pgdata = self.directory / 'pgdata'
            password = secrets.token_hex(24)
            password_file = self.directory / 'pg-password'
            password_file.touch(mode=0o600)
            password_file.write_text(password)
            pgserver.initdb(['--auth-host=scram-sha-256', '--auth-local=scram-sha-256',
                             '--encoding=UTF8', '-U', 'postgres', '--pwfile', str(password_file)],
                            pgdata=pgdata, timeout=30)
            password_file.unlink()
            pgport = unused_port()
            pgserver.pg_ctl(['-w', '-l', str(self.directory / 'postgres.log'),
                             '-o', f'-h 127.0.0.1 -p {pgport} -k /tmp', 'start'],
                            pgdata=pgdata, timeout=30)
            self.pg = pgdata
            self.dsn = f'postgresql://postgres:{password}@127.0.0.1:{pgport}/postgres'
            self.env.update({
                'DATABASE_URL': self.dsn,
                'DIRECT_URL': self.dsn,
                'DATABASE_URL_READER': self.dsn,
                'LITELLM_LICENSE': '',
                'LITELLM_MASTER_KEY': self.master,
                'LITELLM_SALT_KEY': secrets.token_hex(32),
                'UI_USERNAME': 'poc-admin', 'UI_PASSWORD': self.ui_password,
                'POC_UPSTREAM_KEY': self.upstream_key, 'POC_STATS_KEY': self.stats_key,
                'POC_MAAS_BASE': f'http://127.0.0.1:{self.upstream_port}/maas',
                'POC_LOCAL_BASE': f'http://127.0.0.1:{self.upstream_port}/local/v1',
                'LITELLM_LOCAL_MODEL_COST_MAP': 'True',
                'LITELLM_TELEMETRY': 'False',
            })
            # Generate the unmodified official Prisma client in the project virtualenv.
            spec = importlib.util.find_spec('litellm')
            schema = Path(spec.origin).parent / 'proxy' / 'schema.prisma'
            generator = self.spawn([sys.executable, '-m', 'prisma', 'generate', '--schema', str(schema)], 'schema')
            try:
                code = generator.wait(timeout=180)
            except subprocess.TimeoutExpired:
                self.stop_process(generator)
                raise
            if code:
                raise RuntimeError('Prisma generation failed; inspect schema.log')
            self.upstream = self.spawn([sys.executable, '-m', 'uvicorn', 'poc.mock_upstreams:app',
                                       '--host', '127.0.0.1', '--port', str(self.upstream_port)], 'upstream')
            self.wait_ready(f'http://127.0.0.1:{self.upstream_port}/health', self.upstream, 30)
            self.start_proxy()
            self.credentials = {'base_url': self.url, 'master_key': self.master,
                                'ui_username': 'poc-admin', 'ui_password': self.ui_password,
                                'database_url': self.dsn}
            path = self.directory / 'credentials.json'
            path.touch(mode=0o600)
            path.chmod(0o600)
            path.write_text(json.dumps(self.credentials, indent=2) + '\n')
            return self
        except BaseException:
            self.close()
            raise

    def start_proxy(self):
        # Only our freshly created test DB is ever supplied to this command.
        self.proxy = self.spawn([str(Path(sys.executable).parent / 'litellm'),
                                 '--config', str(ROOT / 'poc/config.yaml'),
                                 '--host', '127.0.0.1', '--port', str(self.port),
                                 '--use_prisma_db_push'], 'gateway')
        self.wait_ready(self.url + '/health/liveliness', self.proxy)
        # Liveness alone does not prove DB and key management are usable.
        with httpx.Client(base_url=self.url, trust_env=False, timeout=10) as client:
            response = client.get('/v1/models', headers={'Authorization': f'Bearer {self.master}'})
            if response.status_code != 200:
                raise RuntimeError('Gateway DB/auth not ready; inspect gateway.log')

    def restart_proxy(self):
        self.stop_process(self.proxy)
        self.start_proxy()

    def stats(self):
        return httpx.get(f'http://127.0.0.1:{self.upstream_port}/stats',
                         headers={'x-poc-admin': self.stats_key}, trust_env=False).json()

    def close(self):
        self.stop_process(self.proxy)
        self.stop_process(self.upstream)
        if self.pg is not None:
            pgserver.pg_ctl(['-w', '-m', 'fast', 'stop'], pgdata=self.pg, timeout=30)
            self.pg = None
        for handle in self.handles:
            handle.close()
        self.handles.clear()
