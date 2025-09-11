import re
import logging
import uuid
import os
import certifi
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import session, has_request_context, current_app, url_for, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from werkzeug.routing import BuildError
from wtforms import ValidationError
from flask_login import current_user

# Initialize extensions
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['5000 per day', '500 per hour'],
    storage_uri=os.getenv('REDIS_URI', 'memory://')  # Use Redis for production
)

# Set up logging
root_logger = logging.getLogger('bizcore_app')
root_logger.setLevel(logging.INFO)

class SessionFormatter(logging.Formatter):
    def format(self, record):
        record.session_id = getattr(record, 'session_id', 'no-session-id')
        record.ip_address = getattr(record, 'ip_address', 'unknown')
        record.user_role = getattr(record, 'user_role', 'anonymous')
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(SessionFormatter(
    '[%(asctime)s] %(levelname)s in %(name)s: %(message)s [session: %(session_id)s, role: %(user_role)s, ip: %(ip_address)s]'
))
root_logger.handlers = []
root_logger.addHandler(handler)

class SessionAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs['extra'] = kwargs.get('extra', {})
        session_id = 'no-session-id'
        ip_address = 'unknown'
        user_role = 'anonymous'
        try:
            if has_request_context():
                session_id = session.get('sid', 'no-session-id')
                ip_address = request.remote_addr
                user_role = current_user.role if current_user.is_authenticated else 'anonymous'
            else:
                session_id = f'non-request-{str(uuid.uuid4())[:8]}'
        except Exception as e:
            session_id = f'session-error-{str(uuid.uuid4())[:8]}'
            kwargs['extra']['session_error'] = str(e)
        kwargs['extra']['session_id'] = session_id
        kwargs['extra']['ip_address'] = ip_address
        kwargs['extra']['user_role'] = user_role
        return msg, kwargs

logger = SessionAdapter(root_logger, {})

# Navigation lists
TRADER_TOOLS = [
    {
        "endpoint": "dashboard.index",
        "label": "Dashboard",
        "label_key": "dashboard_summary",
        "description_key": "dashboard_summary_desc",
        "tooltip_key": "dashboard_tooltip",
        "icon": "bi-bar-chart-line"
    },  
    {
        "endpoint": "receipts.index",
        "label": "Receipts",
        "label_key": "receipts_dashboard",
        "description_key": "receipts_dashboard_desc",
        "tooltip_key": "receipts_tooltip",
        "icon": "bi-cash-coin"
    },
    {
        "endpoint": "debtors.index",
        "label": "Debtors",
        "label_key": "debtors_dashboard",
        "description_key": "debtors_dashboard_desc",
        "tooltip_key": "debtors_tooltip",
        "icon": "bi-person-plus"
    },
    {
        "endpoint": "creditors.index",
        "label": "Creditors",
        "label_key": "creditors_dashboard",
        "description_key": "creditors_dashboard_desc",
        "tooltip_key": "creditors_tooltip",
        "icon": "bi-arrow-up-circle"
    },
    {
        "endpoint": "inventory.index",
        "label": "Inventory",
        "label_key": "inventory_dashboard",
        "description_key": "inventory_dashboard_desc",
        "tooltip_key": "inventory_tooltip",
        "icon": "bi-box-seam"
    },
    {
        "endpoint": "payments.index",
        "label": "Payments",
        "label_key": "payments_dashboard",
        "description_key": "payments_dashboard_desc",
        "tooltip_key": "payments_tooltip",
        "icon": "bi-calculator"
    },
    {
        "endpoint": "reports.index",
        "label": "Profit Summary",
        "label_key": "profit_summary",
        "description_key": "profit_summary_desc",
        "tooltip_key": "profit_summary_tooltip",
        "icon": "bi-graph-up-arrow"
    }
]

TRADER_NAV = [
        {
        "endpoint": "receipts.index",
        "label": "Receipts",
        "label_key": "receipts_dashboard",
        "description_key": "receipts_dashboard_desc",
        "tooltip_key": "receipts_tooltip",
        "icon": "bi-cash-coin"
    },
    {
        "endpoint": "debtors.index",
        "label": "Debtors",
        "label_key": "debtors_dashboard",
        "description_key": "debtors_dashboard_desc",
        "tooltip_key": "debtors_tooltip",
        "icon": "bi-person-plus"
    },
    {
        "endpoint": "reports.index",
        "label": "Profit Summary",
        "label_key": "profit_summary",
        "description_key": "profit_summary_desc",
        "tooltip_key": "profit_summary_tooltip",
        "icon": "bi-graph-up-arrow"
    },
    {
        "endpoint": "settings.profile",
        "label": "Profile",
        "label_key": "profile_settings",
        "description_key": "profile_settings_desc",
        "tooltip_key": "profile_tooltip",
        "icon": "bi-person"
    }
]

ADMIN_TOOLS = [
    {
        "endpoint": "dashboard.index",
        "label": "Dashboard",
        "label_key": "dashboard_summary",
        "description_key": "dashboard_summary_desc",
        "tooltip_key": "dashboard_tooltip",
        "icon": "bi-bar-chart-line"
    },
    {
        "endpoint": "admin.dashboard",
        "label": "Dashboard",
        "label_key": "admin_dashboard",
        "description_key": "admin_dashboard_desc",
        "tooltip_key": "admin_dashboard_tooltip",
        "icon": "bi-speedometer"
    },
    {
        "endpoint": "admin.manage_users",
        "label": "Manage Users",
        "label_key": "admin_manage_users",
        "description_key": "admin_manage_users_desc",
        "tooltip_key": "admin_manage_users_tooltip",
        "icon": "bi-people"
    }
]

ADMIN_NAV = [
    {
        "endpoint": "admin.dashboard",
        "label": "Dashboard",
        "label_key": "admin_dashboard",
        "description_key": "admin_dashboard_desc",
        "tooltip_key": "admin_dashboard_tooltip",
        "icon": "bi-speedometer"
    },
    {
        "endpoint": "admin.manage_users",
        "label": "Users",
        "label_key": "admin_manage_users",
        "description_key": "admin_manage_users_desc",
        "tooltip_key": "admin_manage_users_tooltip",
        "icon": "bi-people"
    }
]

ALL_TOOLS = []

def initialize_tools_with_urls(app):
    global TRADER_TOOLS, TRADER_NAV, ADMIN_TOOLS, ADMIN_NAV, ALL_TOOLS
    try:
        with app.app_context():
            TRADER_TOOLS = generate_tools_with_urls(TRADER_TOOLS)
            TRADER_NAV = generate_tools_with_urls(TRADER_NAV)
            ADMIN_TOOLS = generate_tools_with_urls(ADMIN_TOOLS)
            ADMIN_NAV = generate_tools_with_urls(ADMIN_NAV)
            ALL_TOOLS = TRADER_TOOLS + ADMIN_TOOLS
            logger.info('Initialized tools and navigation with resolved URLs', extra={'session_id': 'no-session-id'})
    except Exception as e:
        logger.error(f'Error initializing tools with URLs: {str(e)}', extra={'session_id': 'no-session-id'})
        raise

def generate_tools_with_urls(tools):
    result = []
    for tool in tools:
        try:
            if not tool.get('endpoint'):
                logger.error(f"Missing endpoint for tool {tool.get('label', 'unknown')}", extra={'session_id': 'no-session-id'})
                continue
            url = url_for(tool['endpoint'], _external=True)
            icon = tool.get('icon', 'bi-question-circle')
            if not icon or not icon.startswith('bi-'):
                logger.warning(f"Invalid icon for tool {tool.get('label', 'unknown')}: {icon}", extra={'session_id': 'no-session-id'})
                icon = 'bi-question-circle'
            result.append({**tool, 'url': url, 'icon': icon})
        except BuildError as e:
            logger.error(f"Failed to generate URL for endpoint {tool.get('endpoint', 'unknown')}: {str(e)}", extra={'session_id': 'no-session-id'})
            result.append({**tool, 'url': '#', 'icon': tool.get('icon', 'bi-question-circle')})
    return result

def get_explore_features():
    try:
        features = []
        user_role = 'unauthenticated'
        if has_request_context() and current_user.is_authenticated:
            user_role = current_user.role

        if user_role == 'unauthenticated':
            business_tool_keys = ["debtors_dashboard", "receipts_dashboard", "profit_summary"]  # Removed "business_reports"
            for tool in TRADER_TOOLS:
                if tool["label_key"] in business_tool_keys:
                    features.append({
                        "category": "Business",
                        "label_key": tool["label_key"],
                        "description_key": tool["description_key"],
                        "label": tool["label"],
                        "description": tool.get("description", "Description not available"),
                        "url": tool["url"] if tool["url"] != "#" else url_for("users.login", _external=True)
                    })
        elif user_role == 'trader':
            for tool in TRADER_TOOLS:
                features.append({
                    "category": "Business",
                    "label_key": tool["label_key"],
                    "description_key": tool["description_key"],
                    "label": tool["label"],
                    "description": tool.get("description", "Description not available"),
                    "url": tool["url"]
                })
        elif user_role == 'admin':
            for tool in ADMIN_TOOLS:
                features.append({
                    "category": "Admin",
                    "label_key": tool["label_key"],
                    "description_key": tool["description_key"],
                    "label": tool["label"],
                    "description": tool.get("description", "Description not available"),
                    "url": tool["url"]
                })

        logger.info(f"Retrieved explore features for role: {user_role}", extra={'session_id': session.get('sid', 'no-session-id'), 'user_role': user_role})
        return features
    except Exception as e:
        logger.error(f"Error retrieving explore features for role {user_role}: {str(e)}", extra={'session_id': session.get('sid', 'no-session-id'), 'user_role': user_role})
        return []

def get_limiter():
    return limiter

def format_percentage(value):
    """Format a decimal as a percentage (e.g., 0.25 -> 25%)."""
    try:
        return "{:.2f}%".format(float(value) * 100)
    except (ValueError, TypeError):
        return "0.00%"

def log_tool_usage(action, tool_name=None, details=None, user_id=None, db=None, session_id=None):
    try:
        if db is None:
            db = get_mongo_db()
        if not action or not isinstance(action, str):
            raise ValueError("Action must be a non-empty string")
        effective_session_id = session_id or session.get('sid', 'no-session-id') if has_request_context() else 'no-session-id'
        log_entry = {
            'tool_name': tool_name or action,
            'user_id': str(user_id) if user_id else None,
            'session_id': effective_session_id,
            'action': details.get('action') if details else None,
            'timestamp': datetime.now(ZoneInfo("UTC")),
            'ip_address': request.remote_addr if has_request_context() else 'unknown',
            'user_agent': request.headers.get('User-Agent') if has_request_context() else 'unknown'
        }
        db.tool_usage.insert_one(log_entry)
        logger.info(f"Logged tool usage: {action}", extra={'session_id': effective_session_id, 'user_id': user_id or 'none'})
    except Exception as e:
        logger.error(f"Failed to log tool usage for action {action}: {str(e)}", extra={'session_id': session_id or 'no-session-id'})
        raise RuntimeError(f"Failed to log tool usage: {str(e)}")

def create_anonymous_session():
    try:
        with current_app.app_context():
            session['sid'] = str(uuid.uuid4())
            session['is_anonymous'] = True
            session['created_at'] = datetime.now(ZoneInfo("UTC")).isoformat()
            if 'lang' not in session:
                session['lang'] = 'en'
            session.modified = True
            logger.info(f"Created anonymous session: {session['sid']}", extra={'session_id': session['sid']})
    except Exception as e:
        logger.error(f"Error creating anonymous session: {str(e)}", extra={'session_id': 'error-session'})
        session['sid'] = f'error-{str(uuid.uuid4())[:8]}'
        session['is_anonymous'] = True
        session.modified = True

def clean_currency(value, max_value=10000000000):
    try:
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return 0.0
        if isinstance(value, (int, float)):
            value = float(value)
            if value > max_value:
                raise ValidationError(f"Input cannot exceed {max_value:,}")
            if value < 0:
                raise ValidationError("Negative currency values are not allowed")
            return value
        value_str = str(value).strip()
        cleaned = re.sub(r'[^\d.]', '', value_str.replace('NGN', '').replace('₦', '').replace('$', '').replace('€', '').replace('£', '').replace(',', ''))
        parts = cleaned.split('.')
        if len(parts) > 2 or cleaned.count('-') > 1 or (cleaned.count('-') == 1 and not cleaned.startswith('-')):
            raise ValidationError('Invalid currency format')
        if not cleaned or cleaned == '.':
            raise ValidationError('Invalid currency format')
        result = float(cleaned)
        if result < 0:
            raise ValidationError('Negative currency values are not allowed')
        if result > max_value:
            raise ValidationError(f"Input cannot exceed {max_value:,}")
        return result
    except Exception as e:
        logger.error(f"Error in clean_currency for value '{value}': {str(e)}", extra={'session_id': session.get('sid', 'no-session-id')})
        raise ValidationError('Invalid currency format')

def is_valid_email(email):
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None

def get_mongo_db():
    try:
        with current_app.app_context():
            if 'mongo' not in current_app.extensions:
                mongo_uri = os.getenv('MONGO_URI')
                if not mongo_uri:
                    logger.error("MONGO_URI environment variable not set", extra={'session_id': 'no-session-id'})
                    raise RuntimeError("MONGO_URI environment variable not set")
                client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=5000,
                    tls=True,
                    tlsCAFile=certifi.where(),
                    maxPoolSize=50,
                    minPoolSize=5,
                    connect=False  # Defer connection for fork-safety
                )
                client.admin.command('ping')  # Force connection here
                current_app.extensions['mongo'] = client
                logger.info("MongoClient initialized for worker", extra={'session_id': 'no-session-id'})
            db = current_app.extensions['mongo']['bizdb']
            db.command('ping')
            return db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}", extra={'session_id': 'no-session-id'})
        raise RuntimeError(f"Failed to connect to MongoDB: {str(e)}")

def requires_role(role):
    def decorator(f):
        from functools import wraps
        from flask import redirect, url_for, flash
        @wraps(f)
        def decorated_function(*args, **kwargs):
            with current_app.app_context():
                if not current_user.is_authenticated:
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('users.login'))
                if is_admin():
                    return f(*args, **kwargs)
                allowed_roles = role if isinstance(role, list) else [role]
                if current_user.role not in allowed_roles:
                    flash('You do not have permission to access this page.', 'danger')
                    return redirect(url_for('dashboard.index'))
                if not current_user.is_trial_active():
                    logger.info(f"User {current_user.id} trial expired, redirecting to subscription", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': current_user.id})
                    return redirect(url_for('subscribe_bp.subscription_required'))
                return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_admin():
    try:
        with current_app.app_context():
            return current_user.is_authenticated and current_user.role == 'admin'
    except Exception:
        return False

def can_user_interact(user):
    try:
        with current_app.app_context():
            if not user or not user.is_authenticated:
                logger.info("User interaction denied: No authenticated user", extra={'session_id': session.get('sid', 'no-session-id')})
                return False
            if user.role == 'admin':
                logger.info(f"User {user.id} allowed to interact: Admin role", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
                return True
            if user.get('is_subscribed', False):
                subscription_end = user.get('subscription_end')
                if subscription_end:
                    subscription_end_aware = (
                        subscription_end.replace(tzinfo=ZoneInfo("UTC"))
                        if subscription_end.tzinfo is None
                        else subscription_end
                    )
                    if subscription_end_aware > datetime.now(ZoneInfo("UTC")):
                        logger.info(f"User {user.id} allowed to interact: Active subscription", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
                        return True
                    logger.info(f"User {user.id} subscription expired: {subscription_end_aware}", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
                else:
                    logger.info(f"User {user.id} allowed to interact: Active subscription (no end date)", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
                    return True
            if user.get('is_trial', False):
                trial_end = user.get('trial_end')
                if trial_end:
                    trial_end_aware = (
                        trial_end.replace(tzinfo=ZoneInfo("UTC"))
                        if trial_end.tzinfo is None
                        else trial_end
                    )
                    if trial_end_aware > datetime.now(ZoneInfo("UTC")):
                        logger.info(f"User {user.id} allowed to interact: Active trial", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
                        return True
                    logger.info(f"User {user.id} trial expired: {trial_end_aware}", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
            logger.info(f"User {user.id} interaction denied: No active subscription or trial", extra={'session_id': session.get('sid', 'no-session-id'), 'user_id': user.id})
            return False
    except Exception as e:
        logger.error(f"Error checking user interaction for user {user.get('id', 'unknown')}: {str(e)}", extra={'session_id': session.get('sid', 'no-session-id')})
        return False

def should_show_subscription_banner(user):
    try:
        with current_app.app_context():
            if not user or not user.is_authenticated:
                return False
            if user.role == 'admin':
                return False
            if user.get('is_subscribed', False):
                subscription_end = user.get('subscription_end')
                if subscription_end:
                    subscription_end_aware = (
                        subscription_end.replace(tzinfo=ZoneInfo("UTC"))
                        if subscription_end.tzinfo is None
                        else subscription_end
                    )
                    if subscription_end_aware > datetime.now(ZoneInfo("UTC")):
                        return False
                else:
                    return False
            if user.get('is_trial', False):
                trial_end = user.get('trial_end')
                if trial_end:
                    trial_end_aware = (
                        trial_end.replace(tzinfo=ZoneInfo("UTC"))
                        if trial_end.tzinfo is None
                        else trial_end
                    )
                    if trial_end_aware > datetime.now(ZoneInfo("UTC")):
                        return False
            return True
    except Exception as e:
        logger.error(f"Error checking subscription banner for user {user.get('id', 'unknown')}: {str(e)}", extra={'session_id': session.get('sid', 'no-session-id')})
        return False

def format_currency(amount, currency='₦', lang=None, include_symbol=True):
    try:
        with current_app.app_context():
            if lang is None:
                lang = session.get('lang', 'en') if has_request_context() else 'en'
            if amount is None or amount == '':
                amount = 0
            if isinstance(amount, str):
                amount = clean_currency(amount)
            else:
                amount = float(amount)
            if amount.is_integer():
                formatted = f"{int(amount):,}"
            else:
                formatted = f"{amount:,.2f}"
            return f"{currency}{formatted}" if include_symbol else formatted
    except Exception as e:
        logger.warning(f"Error formatting currency {amount}: {str(e)}", extra={'session_id': session.get('sid', 'no-session-id')})
        return f"{currency}0" if include_symbol else "0"

def format_date(date_obj, lang=None, format_type='short'):
    try:
        with current_app.app_context():
            if lang is None:
                lang = session.get('lang', 'en') if has_request_context() else 'en'
            if not date_obj:
                return ''
            if isinstance(date_obj, str):
                try:
                    date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
                except ValueError:
                    try:
                        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Invalid date format for input: {date_obj}", extra={'session_id': session.get('sid', 'no-session-id')})
                        return date_obj
            date_obj_aware = date_obj.replace(tzinfo=ZoneInfo("UTC")) if date_obj.tzinfo is None else date_obj
            if format_type == 'iso':
                return date_obj_aware.strftime('%Y-%m-%d')
            elif format_type == 'long':
                return date_obj_aware.strftime('%d %B %Y' if lang == 'ha' else '%B %d, %Y')
            else:
                return date_obj_aware.strftime('%d/%m/%Y' if lang == 'ha' else '%m/%d/%Y')
    except Exception as e:
        logger.warning(f"Error formatting date {date_obj}: {str(e)}", extra={'session_id': session.get('sid', 'no-session-id')})
        return str(date_obj) if date_obj else ''

def sanitize_input(input_string, max_length=None):
    if not input_string:
        return ''
    sanitized = str(input_string).strip()
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    if re.search(r'[<>]', sanitized):
        logger.warning(f"Potential malicious input detected: {sanitized}", extra={'session_id': session.get('sid', 'no-session-id')})
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized

def generate_unique_id(prefix=''):
    return f"{prefix}_{str(uuid.uuid4())}" if prefix else str(uuid.uuid4())

def validate_required_fields(data, required_fields):
    missing_fields = [field for field in required_fields if field not in data or not data[field] or str(data[field]).strip() == '']
    return len(missing_fields) == 0, missing_fields

def get_user_language():
    try:
        with current_app.app_context():
            return session.get('lang', 'en') if has_request_context() else 'en'
    except Exception:
        return 'en'

def log_user_action(action, details=None, user_id=None):
    try:
        with current_app.app_context():
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            session_id = session.get('sid', 'no-session-id') if has_request_context() else 'no-session-id'
            log_entry = {
                'user_id': user_id,
                'session_id': session_id,
                'action': action,
                'details': details or {},
                'timestamp': datetime.now(ZoneInfo("UTC")),
                'ip_address': request.remote_addr if has_request_context() else None,
                'user_agent': request.headers.get('User-Agent') if has_request_context() else None
            }
            db = get_mongo_db()
            db.audit_logs.insert_one(log_entry)
            logger.info(f"User action logged: {action} by user {user_id}", extra={'session_id': session_id, 'user_id': user_id or 'none'})
    except Exception as e:
        logger.error(f"Error logging user action: {str(e)}", extra={'session_id': session_id or 'no-session-id'})
        raise

def track_user_activity(activity_type, description, amount=None, related_id=None, user_id=None):
    try:
        with current_app.app_context():
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            if not user_id:
                logger.warning("Cannot track activity: no user ID provided")
                return
            session_id = session.get('sid', 'no-session-id') if has_request_context() else 'no-session-id'
            activity_entry = {
                'user_id': user_id,
                'session_id': session_id,
                'type': activity_type,
                'description': description,
                'amount': amount,
                'related_id': related_id,
                'timestamp': datetime.now(ZoneInfo("UTC")),
                'ip_address': request.remote_addr if has_request_context() else None
            }
            db = get_mongo_db()
            db.user_activities.insert_one(activity_entry)
            log_user_action(f"activity_{activity_type}", {
                'description': description,
                'amount': amount,
                'related_id': related_id
            }, user_id)
            logger.info(f"User activity tracked: {activity_type} for user {user_id}", 
                       extra={'session_id': session_id, 'user_id': user_id})
    except Exception as e:
        logger.error(f"Error tracking user activity: {str(e)}", 
                    extra={'session_id': session.get('sid', 'no-session-id') if has_request_context() else 'no-session-id'})
        # Don't raise to avoid breaking main functionality

__all__ = [
    'clean_currency', 'log_tool_usage', 'get_limiter', 'create_anonymous_session', 
    'is_valid_email', 'get_mongo_db', 'requires_role', 'is_admin', 'can_user_interact',
    'should_show_subscription_banner', 'format_currency', 'format_date', 'sanitize_input', 
    'generate_unique_id', 'validate_required_fields', 'get_user_language', 'log_user_action', 
    'track_user_activity', 'initialize_tools_with_urls', 'TRADER_TOOLS', 'TRADER_NAV', 
    'ADMIN_TOOLS', 'ADMIN_NAV', 'ALL_TOOLS', 'get_explore_features'
]
