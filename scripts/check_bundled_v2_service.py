"""Launch the bundled private backend, check readiness/auth, stop only its process."""
from pathlib import Path
import socket
import json
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
service = root / 'artifacts/windows-v2/service/zakaria_service/zakaria_service.exe'
data = root / 'storage/v2-desktop'
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 8765))
log = root / 'storage/v2-desktop/bundled-service-smoke.log'
with log.open('w', encoding='utf-8') as output:
    process = subprocess.Popen([str(service), '--data-dir', str(data)],
                               cwd=service.parent, stdout=output, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        ready = False
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError('Bundled service exited. See ' + str(log))
            try:
                with urlopen('http://127.0.0.1:8765/api/health/', timeout=1) as response:
                    health = json.load(response)
                    ready = response.status == 200 and health['version'] == '2.1.0' and health['mode'] == 'desktop-register'
                if ready:
                    break
            except (URLError, TimeoutError):
                pass
            time.sleep(.5)
        assert ready, 'Bundled service did not become ready'
        print('PASS: frozen backend health returns 200', flush=True)
        try:
            urlopen('http://127.0.0.1:8765/api/register/entries/', timeout=5)
            raise AssertionError('Unauthenticated business access must be denied')
        except HTTPError as error:
            assert error.code == 401, error.code
        print('PASS: frozen backend protects business endpoint with 401', flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
print('Stopped only the smoke-test backend; browser acceptance services remain running.')
