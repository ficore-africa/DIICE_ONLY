from flask import Blueprint, render_template, current_app, flash, redirect, url_for, session, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from utils import get_mongo_db, logger
from translations import trans
from bson import ObjectId

rewards_bp = Blueprint('rewards', __name__, url_prefix='/rewards')

@rewards_bp.route('/')
@login_required
def index():
    try:
        db = get_mongo_db()
        user_id = current_user.id

        # Fetch user rewards data
        rewards_data = db.rewards.find_one({'user_id': user_id})
        streak = rewards_data.get('streak', 0) if rewards_data else 0
        points = rewards_data.get('points', 0) if rewards_data else 0
        last_activity_date = rewards_data.get('last_activity_date') if rewards_data else None

        # Calculate current streak
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        has_today_activity = False

        # Check for transactions today (records or cashflows)
        transaction_types = ['debtor', 'creditor', 'fund', 'receipt', 'payment']
        today_start = today
        today_end = today + timedelta(days=1)

        records_count = db.records.count_documents({
            'user_id': user_id,
            'type': {'$in': transaction_types},
            'created_at': {'$gte': today_start, '$lt': today_end}
        })
        cashflows_count = db.cashflows.count_documents({
            'user_id': user_id,
            'type': {'$in': ['receipt', 'payment']},
            'created_at': {'$gte': today_start, '$lt': today_end}
        })

        has_today_activity = records_count > 0 or cashflows_count > 0

        # Update streak and points
        if has_today_activity:
            if last_activity_date:
                last_activity_date = last_activity_date.replace(hour=0, minute=0, second=0, microsecond=0)
                if last_activity_date == today - timedelta(days=1):
                    streak += 1
                elif last_activity_date < today - timedelta(days=1):
                    streak = 1
                # Else streak remains the same if already updated today
            else:
                streak = 1
            points += 1
            db.rewards.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'streak': streak,
                        'points': points,
                        'last_activity_date': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
        elif last_activity_date and last_activity_date < today - timedelta(days=1):
            # Reset streak if no activity today and last activity was before yesterday
            db.rewards.update_one(
                {'user_id': user_id},
                {'$set': {'streak': 0, 'updated_at': datetime.now(timezone.utc)}},
                upsert=True
            )
            streak = 0

        # Check for redemption eligibility
        can_redeem = points >= 100
        discount_applied = current_user.get('discount_applied', False)

        return render_template(
            'rewards/index.html',
            streak=streak,
            points=points,
            can_redeem=can_redeem and not discount_applied,
            discount_applied=discount_applied
        )
    except Exception as e:
        logger.error(f"Error loading rewards for user {user_id}: {str(e)}",
                     extra={'session_id': session.get('sid', 'no-session-id'), 'ip_address': request.remote_addr})
        flash(trans('general_error', default='An error occurred while loading your rewards.'), 'danger')
        return redirect(url_for('dashboard.index'))

@rewards_bp.route('/redeem', methods=['POST'])
@login_required
def redeem_points():
    try:
        db = get_mongo_db()
        user_id = current_user.id
        rewards_data = db.rewards.find_one({'user_id': user_id})
        points = rewards_data.get('points', 0) if rewards_data else 0

        if points < 100:
            flash(trans('rewards_insufficient_points', default='You need at least 100 points to redeem a discount.'), 'warning')
            return redirect(url_for('rewards.index'))

        if current_user.get('discount_applied', False):
            flash(trans('rewards_already_redeemed', default='You have already redeemed a discount.'), 'warning')
            return redirect(url_for('rewards.index'))

        # Apply discount
        db.users.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'discount_applied': True,
                    'discount_percentage': 30,
                    'discount_expiry': datetime.now(timezone.utc) + timedelta(days=30)
                }
            }
        )
        db.rewards.update_one(
            {'user_id': user_id},
            {'$inc': {'points': -100}, '$set': {'updated_at': datetime.now(timezone.utc)}}
        )

        flash(trans('rewards_redeemed_success', default='Successfully redeemed 100 points for a 30% discount on your next subscription!'), 'success')
        return redirect(url_for('rewards.index'))
    except Exception as e:
        logger.error(f"Error redeeming points for user {user_id}: {str(e)}",
                     extra={'session_id': session.get('sid', 'no-session-id'), 'ip_address': request.remote_addr})
        flash(trans('general_error', default='An error occurred while redeeming your points.'), 'danger')
        return redirect(url_for('rewards.index'))