import json
import unittest
from unittest.mock import patch

from ui import app as app_mod


class FakeRequest:
    def __init__(self, session=None):
        self.session = session or {}


def body_json(resp):
    return json.loads(resp.body.decode())


class HelpChatV2SmokeTest(unittest.TestCase):
    def test_help_chat_backward_compat_rule_mode(self):
        req = FakeRequest({'user_email': 'u@example.com', 'tenant_id': 'tenant_a'})
        r = app_mod.api_help_chat(req, {'question': 'cooldown คืออะไร'})
        data = body_json(r)
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('mode'), 'rule')
        self.assertIn('Cooldown', data.get('answer', ''))

    def test_help_chat_diagnose_mode(self):
        req = FakeRequest({'user_email': 'u@example.com', 'tenant_id': 'tenant_a'})
        diag = {
            'tenant_id': 'tenant_a',
            'issues': [
                {'title': 'Worker หยุดอยู่', 'severity': 'high', 'why': 'x', 'playbook': ['a', 'b']}
            ],
            'worker': {'running': False},
            'summary': {'entries': 0},
            'blocked_reasons': {},
            'api_test': {'ok': False, 'error': 'no_api_saved'},
        }
        with patch('ui.app._diagnose_tenant', return_value=diag):
            r = app_mod.api_help_chat(req, {'action': 'diagnose_now'})
        data = body_json(r)
        self.assertEqual(data.get('mode'), 'diagnosis')
        self.assertIn('Worker หยุดอยู่', data.get('answer', ''))
        self.assertEqual(data.get('diagnosis', {}).get('tenant_id'), 'tenant_a')

    def test_action_endpoints_authenticated(self):
        req = FakeRequest({'user_email': 'u@example.com', 'tenant_id': 'tenant_a'})
        with patch('ui.app._run_api_test_for_tenant', return_value={'ok': True, 'usdt_total': 12.3}), \
             patch('ui.app.engine_manager.status', return_value={'running': False, 'license_ok': True}), \
             patch('ui.app.engine_manager.start', return_value=True):
            r1 = app_mod.help_action_test_api(req)
            r2 = app_mod.help_action_check_worker(req, {'restart_if_stopped': True})
            r3 = app_mod.help_action_risk_suggestions(req, {'profile': 'balanced'})

        self.assertTrue(body_json(r1).get('ok'))
        self.assertTrue(body_json(r2).get('ok'))
        self.assertIn('message', body_json(r2))
        self.assertTrue(body_json(r3).get('ok'))
        self.assertEqual(body_json(r3).get('apply_mode'), 'manual_only')


if __name__ == '__main__':
    unittest.main()
