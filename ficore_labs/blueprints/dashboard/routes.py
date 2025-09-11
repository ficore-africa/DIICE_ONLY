from flask import Blueprint, render_template, flash, session, jsonify, request
from datetime import timedelta, datetime, timezone
from flask_login import login_required, current_user
from zoneinfo import ZoneInfo
from bson import ObjectId
import logging
from translations import trans
import utils
from utils import format_date
from helpers import reminders

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# API endpoint for weekly profit data (for dashboard chart)
@dashboard_bp.route('/weekly_profit_data')
@login_required
def weekly_profit_data():
    db = utils.get_mongo_db()
    user_id = str(current_user.id)
    today = datetime.now(timezone.utc)
    # Get last 7 days
    days = [(today - timedelta(days=i)).date() for i in range(6, -1, -1)]
    profit_per_day = []
    for day in days:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        # Sum sales and expenses for the day
        sales = db.records.aggregate([
            {'$match': {'user_id': user_id, 'type': 'sale', 'created_at': {'$gte': start, '$lt': end}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        expenses = db.records.aggregate([
            {'$match': {'user_id': user_id, 'type': 'expense', 'created_at': {'$gte': start, '$lt': end}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        sales_total = next(sales, {}).get('total', 0)
        expenses_total = next(expenses, {}).get('total', 0)
        profit = sales_total - expenses_total
        profit_per_day.append({
            'date': day.strftime('%a'),
            'profit': profit
        })
    return jsonify({'data': profit_per_day})

@dashboard_bp.route('/')
@login_required
def index():
    """Display the user's dashboard with recent activity and role-specific content."""
    # Initialize data containers with defaults
    recent_creditors = []
    recent_debtors = []
    recent_payments = []
    recent_receipts = []
    recent_funds = []
    stats = {
        'total_debtors': 0,
        'total_creditors': 0,
        'total_payments': 0,
        'total_receipts': 0,
        'total_funds': 0,
        'total_debtors_amount': 0,
        'total_creditors_amount': 0,
        'total_payments_amount': 0,
        'total_receipts_amount': 0,
        'total_funds_amount': 0,
        'total_forecasts': 0,
        'total_forecasts_amount': 0
    }
    can_interact = False
    show_daily_log_reminder = False
    streak = 0  # Explicitly initialize streak
    unpaid_debtors = []
    unpaid_creditors = []
    inventory_loss = False

    try:
        db = utils.get_mongo_db()
        query = {'user_id': str(current_user.id)}
        tax_prep_mode = request.args.get('tax_prep') == '1'

        # Fetch reminders and streak data
        try:
            show_daily_log_reminder = reminders.needs_daily_log_reminder(db, current_user.id)
            rewards_data = db.rewards.find_one({'user_id': str(current_user.id)})
            streak = rewards_data.get('streak', 0) if rewards_data else 0  # Fetch streak from rewards collection
            unpaid_debtors, unpaid_creditors = reminders.get_unpaid_debts_credits(db, current_user.id)
            inventory_loss = reminders.detect_inventory_loss(db, current_user.id)
            logger.debug(f"Calculated streak: {streak} for user_id: {current_user.id}")
        except Exception as e:
            logger.warning(f"Failed to calculate reminders or streak: {str(e)}", 
                          extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id})
            # Keep defaults for safety
            streak = 0  # Explicitly reset to 0 on failure
            flash(trans('reminder_load_error', default='Unable to load reminders or streak data.'), 'warning')

        # Fetch recent data with error handling
        try:
            if tax_prep_mode:
                # Only show profit (sales-expenses) in stats
                sales = db.records.aggregate([
                    {'$match': {**query, 'type': 'sale'}},
                    {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
                ])
                expenses = db.records.aggregate([
                    {'$match': {**query, 'type': 'expense'}},
                    {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
                ])
                stats['profit_only'] = next(sales, {}).get('total', 0) - next(expenses, {}).get('total', 0)
                stats['total_receipts'] = stats['total_payments'] = stats['total_funds'] = 0
                stats['total_receipts_amount'] = stats['total_payments_amount'] = stats['total_funds_amount'] = 0
            recent_creditors = list(db.records.find({**query, 'type': 'creditor'}).sort('created_at', -1).limit(5))
            recent_debtors = list(db.records.find({**query, 'type': 'debtor'}).sort('created_at', -1).limit(5))
            recent_payments = list(db.cashflows.find({**query, 'type': 'payment'}).sort('created_at', -1).limit(5))
            recent_receipts = list(db.cashflows.find({**query, 'type': 'receipt'}).sort('created_at', -1).limit(5))
            recent_funds = list(db.records.find({**query, 'type': 'fund'}).sort('created_at', -1).limit(5))
        except Exception as e:
            logger.error(f"Error querying MongoDB for dashboard data: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id})
            flash(trans('dashboard_load_error', default='Failed to load some dashboard data. Displaying available information.'), 'warning')

        # Sanitize and convert datetimes
        for item in recent_creditors + recent_debtors:
            try:
                if item.get('created_at') and item['created_at'].tzinfo is None:
                    item['created_at'] = item['created_at'].replace(tzinfo=ZoneInfo("UTC"))
                if item.get('reminder_date') and item['reminder_date'].tzinfo is None:
                    item['reminder_date'] = item['reminder_date'].replace(tzinfo=ZoneInfo("UTC"))
                item['name'] = utils.sanitize_input(item.get('name', ''), max_length=100)
                item['description'] = utils.sanitize_input(item.get('description', 'No description provided'), max_length=500)
                item['contact'] = utils.sanitize_input(item.get('contact', 'N/A'), max_length=50)
                item['_id'] = str(item['_id'])
            except Exception as e:
                logger.warning(f"Error processing creditor/debtor item {item.get('_id')}: {str(e)}")
                continue

        for item in recent_payments + recent_receipts:
            try:
                if item.get('created_at') and item['created_at'].tzinfo is None:
                    item['created_at'] = item['created_at'].replace(tzinfo=ZoneInfo("UTC"))
                item['description'] = utils.sanitize_input(item.get('description', 'No description provided'), max_length=500)
                item['_id'] = str(item['_id'])
            except Exception as e:
                logger.warning(f"Error processing payment/receipt item {item.get('_id')}: {str(e)}")
                continue

        for item in recent_funds:
            try:
                if item.get('created_at') and item['created_at'].tzinfo is None:
                    item['created_at'] = item['created_at'].replace(tzinfo=ZoneInfo("UTC"))
                item['name'] = utils.sanitize_input(item.get('name', ''), max_length=100)
                item['description'] = utils.sanitize_input(item.get('description', 'No description provided'), max_length=500)
                item['_id'] = str(item['_id'])
            except Exception as e:
                logger.warning(f"Error processing fund item {item.get('_id')}: {str(e)}")
                continue

        # Calculate stats with safe access
        try:
            stats.update({
                'total_debtors': db.records.count_documents({**query, 'type': 'debtor'}),
                'total_creditors': db.records.count_documents({**query, 'type': 'creditor'}),
                'total_payments': db.cashflows.count_documents({**query, 'type': 'payment'}),
                'total_receipts': db.cashflows.count_documents({**query, 'type': 'receipt'}),
                'total_funds': db.records.count_documents({**query, 'type': 'fund'}),
                'total_debtors_amount': sum(doc.get('amount_owed', 0) for doc in db.records.find({**query, 'type': 'debtor'})),
                'total_creditors_amount': sum(doc.get('amount_owed', 0) for doc in db.records.find({**query, 'type': 'creditor'})),
                'total_payments_amount': sum(doc.get('amount', 0) for doc in db.cashflows.find({**query, 'type': 'payment'})),
                'total_receipts_amount': sum(doc.get('amount', 0) for doc in db.cashflows.find({**query, 'type': 'receipt'})),
                'total_funds_amount': sum(doc.get('amount', 0) for doc in db.records.find({**query, 'type': 'fund'})),
                'total_forecasts': db.records.count_documents({**query, 'type': 'forecast'}),
                'total_forecasts_amount': sum(doc.get('projected_revenue', 0) for doc in db.records.find({**query, 'type': 'forecast'}))
            })
        except Exception as e:
            logger.error(f"Error calculating stats for dashboard: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id})
            flash(trans('dashboard_stats_error', default='Unable to calculate dashboard statistics. Displaying defaults.'), 'warning')

        # Check subscription status
        try:
            can_interact = utils.can_user_interact(current_user)
        except Exception as e:
            logger.error(f"Error checking user interaction status: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id})
            flash(trans('interaction_check_error', default='Unable to verify interaction status.'), 'warning')

        # Render dashboard with all required variables
        return render_template(
            'dashboard/index.html',
            recent_creditors=recent_creditors,
            recent_debtors=recent_debtors,
            recent_payments=recent_payments,
            recent_receipts=recent_receipts,
            recent_funds=recent_funds,
            stats=stats,
            can_interact=can_interact,
            show_daily_log_reminder=show_daily_log_reminder,
            streak=streak,  # Always defined
            unpaid_debtors=unpaid_debtors,
            unpaid_creditors=unpaid_creditors,
            tax_prep_mode=tax_prep_mode,
            inventory_loss=inventory_loss
        )

    except Exception as e:
        # Fallback for critical errors
        logger.critical(f"Critical error in dashboard route: {str(e)}", 
                       extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id})
        flash(trans('dashboard_critical_error', default='An error occurred while loading the dashboard. Please try again later.'), 'danger')
        return render_template(
            'dashboard/index.html',
            recent_creditors=[],
            recent_debtors=[],
            recent_payments=[],
            recent_receipts=[],
            recent_funds=[],
            stats=stats,
            can_interact=False,
            show_daily_log_reminder=False,
            streak=0,  # Ensure streak is defined in fallback
            unpaid_debtors=[],
            unpaid_creditors=[],
            tax_prep_mode=False,
            inventory_loss=False
        )
