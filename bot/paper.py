paper_log = []

def record_trade(action, price, reason):
    trade = {
        "action": action,
        "price": price,
        "reason": reason
    }
    paper_log.append(trade)
    print("📝 PAPER TRADE:", trade)
