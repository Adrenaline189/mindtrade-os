#!/usr/bin/env python3
"""Smoke test: signup -> trial license -> admin visibility -> API save/test -> worker start."""

from __future__ import annotations

import time
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from ui.app import app
from bot.auth_service import resolve_user_tenant
from bot.engine_manager import engine_manager


def main() -> int:
    email = f"smoke_flow_{int(time.time())}@example.com"
    password = "Passw0rd!"

    with TestClient(app) as client:
        r = client.post('/auth/signup', data={'email': email, 'password': password}, follow_redirects=False)
        assert r.status_code in (302, 303), f"signup failed status={r.status_code}"

        profile = client.get('/profile')
        txt = profile.text
        assert profile.status_code == 200, "profile page unavailable"
        assert email in txt, "signup session/email missing"
        assert 'starter_trial' in txt, "trial plan missing on profile"

        tenant_id = resolve_user_tenant(email)
        assert tenant_id, "tenant not resolved"

        admin = client.get('/admin/control')
        admin_txt = admin.text
        assert admin.status_code == 200, "admin control unavailable"
        assert tenant_id in admin_txt, "tenant missing in admin control"
        assert email in admin_txt, "email missing in admin control"

        save_api = client.post('/settings/api/save', data={'api_key': 'k_demo', 'api_secret': 's_demo'}, follow_redirects=False)
        assert save_api.status_code in (302, 303), f"api save failed status={save_api.status_code}"

        class _FakeExchange:
            def fetch_balance(self):
                return {'USDT': {'total': 321.45}}

        with patch('ccxt.binance', return_value=_FakeExchange()):
            t = client.post('/settings/api/test')
            j = t.json()
            assert j.get('ok') is True, f"api test failed: {j}"
            assert float(j.get('usdt_total') or 0) == 321.45, f"unexpected usdt_total: {j}"

        started = client.post('/admin/workers/start', data={'tenant_id': tenant_id})
        sj = started.json()
        assert sj.get('started') is True, f"worker start failed: {sj}"

        st = client.get(f'/admin/workers/{tenant_id}').json()
        assert st.get('running') is True, f"worker not running: {st}"

        stop = client.post('/admin/workers/stop', data={'tenant_id': tenant_id, 'timeout_sec': '3'})
        assert stop.status_code == 200
        engine_manager.stop(tenant_id, timeout_sec=1.0)

    print({
        'ok': True,
        'email': email,
        'tenant_id': tenant_id,
        'checks': [
            'signup_ok',
            'trial_license_visible',
            'admin_visibility_ok',
            'api_save_ok',
            'api_test_ok',
            'worker_start_ok',
        ],
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
