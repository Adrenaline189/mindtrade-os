import tempfile
import unittest
from pathlib import Path

from bot import license_service as ls


class PaymentFlowSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = ls.DB
        ls.DB = Path(self.tmp.name) / 'licenses.json'

    def tearDown(self):
        ls.DB = self.old_db
        self.tmp.cleanup()

    def test_manual_approve_idempotent(self):
        order = ls.create_payment_order('u@example.com', 'starter', 29.0, 'promptpay')
        out1 = ls.activate_or_renew_license_by_order(order['order_id'], source='admin', idempotency_key=f"admin_approve:{order['order_id']}")
        out2 = ls.activate_or_renew_license_by_order(order['order_id'], source='admin', idempotency_key=f"admin_approve:{order['order_id']}")
        self.assertTrue(out1.get('ok'))
        self.assertTrue(out2.get('ok'))
        self.assertTrue(out2.get('duplicate'))
        updated = ls.get_payment_order(order['order_id'])
        self.assertEqual(updated['status'], 'paid')

    def test_webhook_signature_and_event_idempotent(self):
        payload = b'{"event_id":"evt_1","order_id":"ord_1","status":"paid"}'
        secret = 'abc123'
        import hmac, hashlib
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        self.assertTrue(ls.verify_binancepay_signature(payload, sig, secret))
        self.assertFalse(ls.verify_binancepay_signature(payload, 'wrong', secret))

        self.assertFalse(ls.is_processed_event('evt_1'))
        self.assertTrue(ls.mark_processed_event('evt_1'))
        self.assertTrue(ls.is_processed_event('evt_1'))
        self.assertFalse(ls.mark_processed_event('evt_1'))


if __name__ == '__main__':
    unittest.main()
