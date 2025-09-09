from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFError
from translations import trans
from models import update_user, get_mongo_db
import requests
import utils
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger('business_finance_app')
logger.setLevel(logging.INFO)

subscribe_bp = Blueprint('subscribe_bp', __name__, url_prefix='/subscribe')

@subscribe_bp.route('/')
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
def subscribe():
    """Render the subscription page with pricing plans."""
    try:
        lang = session.get('lang', 'en')
        plans = [
            {
                'name': trans('subscribe_monthly', lang=lang, default='Monthly Plan'),
                'price': '₦1,000',
                'duration': 'month',
                'description': trans('subscribe_monthly_description', lang=lang, default='Access all features for one month'),
                'plan_code': 'monthly'
            },
            {
                'name': trans('subscribe_yearly', lang=lang, default='Yearly Plan'),
                'price': '₦10,000',
                'duration': 'year',
                'description': trans('subscribe_yearly_description', lang=lang, default='Access all features for one year (save 17%)'),
                'plan_code': 'yearly'
            }
        ]
        logger.info(
            f"Rendering subscription page for user {current_user.id}, is_subscribed: {current_user.is_subscribed}, is_trial_active: {current_user.is_trial_active()}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        return render_template(
            'subscribe/subscribe.html',
            title=trans('subscribe_title', lang=lang, default='Subscribe to FiCore'),
            plans=plans,
            paystack_public_key=os.getenv('PAYSTACK_PUBLIC_KEY')
        )
    except Exception as e:
        logger.error(
            f"Error rendering subscription page for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred while loading the subscription page'), 'danger')
        return redirect(url_for('general_bp.home'))

@subscribe_bp.route('/initiate-payment', methods=['POST'])
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
@utils.limiter.limit('10 per minute')
def initiate_payment():
    """Initiate payment with Paystack."""
    try:
        if not os.getenv('PAYSTACK_SECRET_KEY'):
            logger.error(
                f"Paystack secret key missing for user {current_user.id}",
                extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
            )
            flash(trans('general_error', default='Payment configuration error'), 'danger')
            return redirect(url_for('subscribe_bp.subscribe'))

        plan_code = utils.sanitize_input(request.form.get('plan_code'), max_length=20)
        if plan_code not in ['monthly', 'yearly']:
            logger.error(
                f"Invalid plan code {plan_code} for user {current_user.id}",
                extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
            )
            flash(trans('subscribe_invalid_plan', default='Invalid plan selected'), 'danger')
            return redirect(url_for('subscribe_bp.subscribe'))
        
        amount = 100000 if plan_code == 'monthly' else 1000000  # Amounts in kobo
        reference = utils.sanitize_input(f"ficore_{current_user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}", max_length=100)

        # Prepare Paystack API request
        headers = {
            'Authorization': f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
            'Content-Type': 'application/json'
        }
        payload = {
            'email': utils.sanitize_input(current_user.email, max_length=100),
            'amount': amount,
            'reference': reference,
            'callback_url': url_for('subscribe_bp.callback', _external=True)
        }

        # Initialize Paystack transaction
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            headers=headers,
            json=payload
        )
        response_data = response.json()

        if response.status_code != 200 or not response_data.get('status'):
            logger.error(
                f"Paystack initialization failed for user {current_user.id}: {response_data.get('message', 'Unknown error')}",
                extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
            )
            flash(trans('subscribe_payment_init_error', default='Failed to initiate payment'), 'danger')
            return redirect(url_for('subscribe_bp.subscribe'))

        logger.info(
            f"Payment initiated for user {current_user.id}, reference: {reference}, plan: {plan_code}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        
        # Store pending transaction in session for verification
        session['pending_transaction'] = {
            'reference': reference,
            'plan_code': plan_code,
            'amount': amount
        }

        return jsonify({'authorization_url': response_data['data']['authorization_url']})
    except CSRFError as e:
        logger.error(
            f"CSRF error in initiating payment for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('subscribe_csrf_error', default='Invalid CSRF token. Please try again.'), 'danger')
        return redirect(url_for('subscribe_bp.subscribe'))
    except requests.RequestException as e:
        logger.error(
            f"Paystack API request error for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('subscribe_payment_init_error', default='Failed to initiate payment'), 'danger')
        return redirect(url_for('subscribe_bp.subscribe'))
    except Exception as e:
        logger.error(
            f"Error initiating payment for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred during payment initiation'), 'danger')
        return redirect(url_for('subscribe_bp.subscribe'))

@subscribe_bp.route('/callback')
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
def callback():
    """Handle Paystack payment callback."""
    try:
        reference = request.args.get('reference')
        pending_transaction = session.get('pending_transaction')

        if not reference or not pending_transaction or pending_transaction['reference'] != reference:
            logger.error(
                f"Invalid callback reference {reference} for user {current_user.id}",
                extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
            )
            flash(trans('subscribe_invalid_reference', default='Invalid payment reference'), 'danger')
            session.pop('pending_transaction', None)
            return redirect(url_for('subscribe_bp.subscribe'))

        # Verify transaction with Paystack
        headers = {
            'Authorization': f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers
        )
        response_data = response.json()

        if response.status_code != 200 or not response_data.get('status') or response_data['data']['status'] != 'success':
            logger.error(
                f"Payment verification failed for user {current_user.id}: {response_data.get('message', 'Unknown error')}",
                extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
            )
            flash(trans('subscribe_payment_failed', default='Payment verification failed'), 'danger')
            session.pop('pending_transaction', None)
            return redirect(url_for('subscribe_bp.subscribe'))

        # Update user subscription status
        db = get_mongo_db()
        update_data = {
            'is_subscribed': True,
            'subscription_plan': pending_transaction['plan_code'],
            'subscription_start': datetime.now(timezone.utc),
            'subscription_end': datetime.now(timezone.utc) + timedelta(days=30 if pending_transaction['plan_code'] == 'monthly' else 365)
        }
        update_user(db, current_user.id, update_data)

        # Log audit event
        db.audit_logs.insert_one({
            'admin_id': 'system',
            'action': 'subscription_success',
            'details': {
                'user_id': str(current_user.id),
                'plan_code': pending_transaction['plan_code'],
                'reference': reference,
                'amount': pending_transaction['amount']
            },
            'timestamp': datetime.now(timezone.utc)
        })

        logger.info(
            f"Subscription successful for user {current_user.id}, plan: {pending_transaction['plan_code']}, reference: {reference}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('subscribe_success', default='Subscription successful! You now have full access.'), 'success')
        session.pop('pending_transaction', None)
        return redirect(url_for('general_bp.home'))
    except requests.RequestException as e:
        logger.error(
            f"Paystack API request error in callback for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('subscribe_payment_failed', default='Payment verification failed'), 'danger')
        session.pop('pending_transaction', None)
        return redirect(url_for('subscribe_bp.subscribe'))
    except Exception as e:
        logger.error(
            f"Error processing callback for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred during payment processing'), 'danger')
        session.pop('pending_transaction', None)
        return redirect(url_for('subscribe_bp.subscribe'))

@subscribe_bp.route('/subscription-required')
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
def subscription_required():
    """Render a page indicating that a subscription is required."""
    try:
        lang = session.get('lang', 'en')
        logger.info(
            f"Rendering subscription required page for user {current_user.id}, is_subscribed: {current_user.is_subscribed}, is_trial_active: {current_user.is_trial_active()}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        return render_template(
            'subscribe/subscription_required.html',
            title=trans('subscribe_required_title', lang=lang, default='Subscription Required'),
            can_interact=False
        )
    except Exception as e:
        logger.error(
            f"Error rendering subscription required page for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred while loading the page'), 'danger')
        return redirect(url_for('general_bp.home'))

@subscribe_bp.route('/status')
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
def subscription_status():
    """Render the subscription status page."""
    try:
        lang = session.get('lang', 'en')
        logger.info(
            f"Rendering subscription status page for user {current_user.id}, is_subscribed: {current_user.is_subscribed}, is_trial_active: {current_user.is_trial_active()}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        return render_template(
            'subscribe/subscription_status.html',
            title=trans('subscribe_status_title', lang=lang, default='Subscription Status'),
            is_subscribed=current_user.is_subscribed,
            is_trial_active=current_user.is_trial_active()
        )
    except Exception as e:
        logger.error(
            f"Error rendering subscription status page for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred while loading the subscription status page'), 'danger')
        return redirect(url_for('general_bp.home'))

@subscribe_bp.route('/manage')
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
def manage_subscription():
    """Render the subscription management page with payment info and receipt upload."""
    try:
        lang = session.get('lang', 'en')
        
        # Get payment information from environment variables
        payment_info = {
            'bank': os.getenv('PAYMENT_BANK', 'OPAY'),
            'account_name': os.getenv('PAYMENT_ACCOUNT_NAME', 'Ficore Labs'),
            'account_number': os.getenv('PAYMENT_ACCOUNT_NUMBER', '1234567890')
        }
        
        # Get user's uploaded receipts
        db = get_mongo_db()
        receipts = list(db.payment_receipts.find({'user_id': current_user.id}).sort('uploaded_at', -1))
        
        logger.info(
            f"Rendering subscription management page for user {current_user.id}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        
        return render_template(
            'subscribe/manage_subscription.html',
            title=trans('subscribe_manage_title', lang=lang, default='Manage Subscription'),
            payment_info=payment_info,
            receipts=receipts
        )
    except Exception as e:
        logger.error(
            f"Error rendering subscription management page for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred while loading the subscription management page'), 'danger')
        return redirect(url_for('general_bp.home'))

@subscribe_bp.route('/upload-receipt', methods=['POST'])
@login_required
@utils.requires_role(['trader', 'startup', 'admin'])
@utils.limiter.limit('5 per minute')
def upload_receipt():
    """Handle receipt upload for manual payment verification."""
    try:
        if 'receipt' not in request.files:
            flash(trans('subscribe_no_file', default='No file selected'), 'danger')
            return redirect(url_for('subscribe_bp.manage_subscription'))
        
        file = request.files['receipt']
        if file.filename == '':
            flash(trans('subscribe_no_file', default='No file selected'), 'danger')
            return redirect(url_for('subscribe_bp.manage_subscription'))
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            flash(trans('subscribe_invalid_file', default='Invalid file type. Please upload PNG, JPG, JPEG, or PDF files only.'), 'danger')
            return redirect(url_for('subscribe_bp.manage_subscription'))
        
        # Get form data
        plan_type = utils.sanitize_input(request.form.get('plan_type'), max_length=20)
        amount_paid = utils.sanitize_input(request.form.get('amount_paid'), max_length=20)
        payment_date = utils.sanitize_input(request.form.get('payment_date'), max_length=20)
        
        if not all([plan_type, amount_paid, payment_date]):
            flash(trans('subscribe_missing_info', default='Please fill in all required fields'), 'danger')
            return redirect(url_for('subscribe_bp.manage_subscription'))
        
        # Validate plan type and amount
        valid_plans = {'monthly': 1000, 'yearly': 10000}
        if plan_type not in valid_plans:
            flash(trans('subscribe_invalid_plan', default='Invalid plan selected'), 'danger')
            return redirect(url_for('subscribe_bp.manage_subscription'))
        
        try:
            amount_paid_float = float(amount_paid)
            expected_amount = valid_plans[plan_type]
            if amount_paid_float < expected_amount:
                flash(trans('subscribe_insufficient_amount', default=f'Amount paid is less than required for {plan_type} plan (₦{expected_amount:,})'), 'danger')
                return redirect(url_for('subscribe_bp.manage_subscription'))
        except ValueError:
            flash(trans('subscribe_invalid_amount', default='Invalid amount format'), 'danger')
            return redirect(url_for('subscribe_bp.manage_subscription'))
        
        # Save file
        filename = f"{current_user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        upload_folder = os.path.join(current_app.root_path, 'uploads', 'receipts')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Store receipt info in database
        db = get_mongo_db()
        receipt_data = {
            'user_id': current_user.id,
            'filename': filename,
            'file_path': file_path,
            'plan_type': plan_type,
            'amount_paid': amount_paid_float,
            'payment_date': datetime.strptime(payment_date, '%Y-%m-%d'),
            'status': 'pending',
            'uploaded_at': datetime.now(timezone.utc)
        }
        
        result = db.payment_receipts.insert_one(receipt_data)
        
        # Log the upload
        utils.log_user_action('receipt_uploaded', {
            'receipt_id': str(result.inserted_id),
            'plan_type': plan_type,
            'amount_paid': amount_paid_float
        }, current_user.id)
        
        logger.info(
            f"Receipt uploaded by user {current_user.id}: {filename}, plan: {plan_type}, amount: {amount_paid}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        
        flash(trans('subscribe_receipt_uploaded', default='Receipt uploaded successfully! Admin will review and activate your subscription.'), 'success')
        return redirect(url_for('subscribe_bp.manage_subscription'))
        
    except Exception as e:
        logger.error(
            f"Error uploading receipt for user {current_user.id}: {str(e)}",
            extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id}
        )
        flash(trans('general_error', default='An error occurred while uploading the receipt'), 'danger')
        return redirect(url_for('subscribe_bp.manage_subscription'))
