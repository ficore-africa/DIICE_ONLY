def detect_inventory_loss(db, user_id):
    """
    Returns True if any inventory record has cost > expected margin (loss detected).
    """
    # Example: inventory records have 'cost' and 'expected_margin' fields
    loss_found = db.records.find_one({
        'user_id': str(user_id),
        'type': 'inventory',
        '$expr': {'$gt': ['$cost', '$expected_margin']}
    })
    return bool(loss_found)
def get_unpaid_debts_credits(db, user_id):
    """
    Returns a list of unpaid debts (debtors) and credits (creditors) for the user.
    """
    # Debtors: people who owe the user (user is creditor)
    unpaid_debtors = list(db.records.find({
        'user_id': str(user_id),
        'type': 'debtor',
        'amount_owed': {'$gt': 0},
        'status': {'$ne': 'paid'}
    }))
    # Creditors: people the user owes (user is debtor)
    unpaid_creditors = list(db.records.find({
        'user_id': str(user_id),
        'type': 'creditor',
        'amount_owed': {'$gt': 0},
        'status': {'$ne': 'paid'}
    }))
    return unpaid_debtors, unpaid_creditors
def get_user_streak(db, user_id):
    """
    Returns the number of consecutive days (including today if logged) the user has logged a sale or expense.
    """
    today = datetime.now(timezone.utc).date()
    streak = 0
    for i in range(0, 30):  # Check up to 30 days back
        day = today - timedelta(days=i)
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        found = db.records.find_one({
            'user_id': str(user_id),
            'type': {'$in': ['sale', 'expense']},
            'created_at': {'$gte': start, '$lt': end}
        })
        if found:
            streak += 1
        else:
            break
    return streak
"""
reminders.py: Utility functions for smart reminders (e.g., daily sales/expenses logging)
"""
from datetime import datetime, timezone

def needs_daily_log_reminder(db, user_id):
    """
    Returns True if the user has not logged a sale or expense today.
    """
    today = datetime.now(timezone.utc).date()
    # Check for sales or expenses logged today
    sales_today = db.records.find_one({
        'user_id': str(user_id),
        'type': {'$in': ['sale', 'expense']},
        'created_at': {'$gte': datetime(today.year, today.month, today.day, tzinfo=timezone.utc)}
    })
    return sales_today is None
