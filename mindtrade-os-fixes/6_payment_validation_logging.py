"""
FIX 6: Add logging when invalid payment status is attempted (potential injection)

In bot/license_service.py, find the update_payment_order_status function
and add logging for invalid status attempts.

REPLACE the beginning of update_payment_order_status with:

def update_payment_order_status(order_id: str, status: str, *, reason: str = '', paid_at: str | None = None, meta: dict | None = None) -> dict | None:
    import logging
    logger = logging.getLogger(__name__)
    
    status_norm = (status or '').strip().lower()
    if status_norm not in {'pending', 'paid', 'failed'}:
        # Security fix: Log attempts to inject invalid status
        logger.warning(
            f"BLOCKED_INVALID_STATUS_ATTEMPT: order_id={order_id!r} "
            f"attempted_status={status!r} reason={reason!r}"
        )
        raise ValueError('invalid_status')

    db = _load()
    changed = None
    for row in db.get('payment_orders', []):
        if row.get('order_id') != order_id:
            continue
        current = (row.get('status') or '').strip().lower()
        
        # Security fix: Log status override attempts
        if current in {'paid', 'failed'} and status_norm != current:
            logger.warning(
                f"BLOCKED_STATUS_OVERRIDE_ATTEMPT: order_id={order_id!r} "
                f"current_status={current!r} attempted_status={status_norm!r}"
            )
            changed = row
            break
        # ... rest of function unchanged
"""
