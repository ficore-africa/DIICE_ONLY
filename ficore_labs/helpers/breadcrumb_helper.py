"""
Breadcrumb navigation helper for generating breadcrumb data based on current route.
"""

from flask import request, url_for
from flask_login import current_user
from werkzeug.routing import BuildError
import logging

logger = logging.getLogger(__name__)

def get_breadcrumb_items():
    """
    Generate breadcrumb items based on the current route.
    Returns a list of breadcrumb items with label, url, and icon.
    """
    try:
        endpoint = request.endpoint
        if not endpoint:
            return []

        breadcrumb_items = []
        
        # Define breadcrumb mappings for different routes
        breadcrumb_map = {
            # Debtors module
            'debtors.index': [
                {'label': 'Debtors', 'label_key': 'debtors_dashboard', 'icon': 'bi-person-plus'}
            ],
            'debtors.add': [
                {'label': 'Debtors', 'label_key': 'debtors_dashboard', 'url': url_for('debtors.index'), 'icon': 'bi-person-plus'},
                {'label': 'Add Debtor', 'label_key': 'debtors_add_debtor', 'icon': 'bi-plus-circle'}
            ],
            'debtors.edit': [
                {'label': 'Debtors', 'label_key': 'debtors_dashboard', 'url': url_for('debtors.index'), 'icon': 'bi-person-plus'},
                {'label': 'Edit Debtor', 'label_key': 'debtors_edit_debtor', 'icon': 'bi-pencil-square'}
            ],
            
            # Creditors module
            'creditors.index': [
                {'label': 'Creditors', 'label_key': 'creditors_dashboard', 'icon': 'bi-arrow-up-circle'}
            ],
            'creditors.add': [
                {'label': 'Creditors', 'label_key': 'creditors_dashboard', 'url': url_for('creditors.index'), 'icon': 'bi-arrow-up-circle'},
                {'label': 'Add Creditor', 'label_key': 'creditors_add_creditor', 'icon': 'bi-plus-circle'}
            ],
            'creditors.edit': [
                {'label': 'Creditors', 'label_key': 'creditors_dashboard', 'url': url_for('creditors.index'), 'icon': 'bi-arrow-up-circle'},
                {'label': 'Edit Creditor', 'label_key': 'creditors_edit_creditor', 'icon': 'bi-pencil-square'}
            ],
            
            # Receipts module
            'receipts.index': [
                {'label': 'Receipts', 'label_key': 'receipts_dashboard', 'icon': 'bi-cash-coin'}
            ],
            'receipts.add': [
                {'label': 'Receipts', 'label_key': 'receipts_dashboard', 'url': url_for('receipts.index'), 'icon': 'bi-cash-coin'},
                {'label': 'Add Receipt', 'label_key': 'receipts_add_receipt', 'icon': 'bi-plus-circle'}
            ],
            'receipts.edit': [
                {'label': 'Receipts', 'label_key': 'receipts_dashboard', 'url': url_for('receipts.index'), 'icon': 'bi-cash-coin'},
                {'label': 'Edit Receipt', 'label_key': 'receipts_edit_receipt', 'icon': 'bi-pencil-square'}
            ],
            
            # Payments module
            'payments.index': [
                {'label': 'Payments', 'label_key': 'payments_dashboard', 'icon': 'bi-calculator'}
            ],
            'payments.add': [
                {'label': 'Payments', 'label_key': 'payments_dashboard', 'url': url_for('payments.index'), 'icon': 'bi-calculator'},
                {'label': 'Add Payment', 'label_key': 'payments_add_payment', 'icon': 'bi-plus-circle'}
            ],
            'payments.edit': [
                {'label': 'Payments', 'label_key': 'payments_dashboard', 'url': url_for('payments.index'), 'icon': 'bi-calculator'},
                {'label': 'Edit Payment', 'label_key': 'payments_edit_payment', 'icon': 'bi-pencil-square'}
            ],
            
            # Reports module
            'reports.index': [
                {'label': 'Reports', 'label_key': 'business_reports', 'icon': 'bi-journal-minus'}
            ],
            'reports.generate': [
                {'label': 'Reports', 'label_key': 'business_reports', 'url': url_for('reports.index'), 'icon': 'bi-journal-minus'},
                {'label': 'Generate Report', 'label_key': 'reports_generate', 'icon': 'bi-file-earmark-plus'}
            ],
            
            # Dashboard module
            'dashboard.index': [
                {'label': 'Dashboard', 'label_key': 'general_dashboard', 'icon': 'bi-speedometer2'}
            ],
            
           
            
            # KYC module
            'kyc.index': [
                {'label': 'KYC Verification', 'label_key': 'kyc_verification', 'icon': 'bi-shield-check'}
            ],
            'kyc.upload': [
                {'label': 'KYC Verification', 'label_key': 'kyc_verification', 'url': url_for('kyc.index'), 'icon': 'bi-shield-check'},
                {'label': 'Upload Documents', 'label_key': 'kyc_upload_documents', 'icon': 'bi-cloud-upload'}
            ],
            
            # Settings module
            'settings.profile': [
                {'label': 'Settings', 'label_key': 'settings_title', 'icon': 'bi-gear'},
                {'label': 'Profile', 'label_key': 'profile_settings', 'icon': 'bi-person'}
            ],
            'settings.security': [
                {'label': 'Settings', 'label_key': 'settings_title', 'url': url_for('settings.profile'), 'icon': 'bi-gear'},
                {'label': 'Security', 'label_key': 'security_settings', 'icon': 'bi-shield-lock'}
            ],
            'settings.business': [
                {'label': 'Settings', 'label_key': 'settings_title', 'url': url_for('settings.profile'), 'icon': 'bi-gear'},
                {'label': 'Business', 'label_key': 'business_settings', 'icon': 'bi-building'}
            ],
            
            # Admin module
            'admin.dashboard': [
                {'label': 'Admin', 'label_key': 'admin_dashboard', 'icon': 'bi-speedometer'}
            ],
            'admin.manage_users': [
                {'label': 'Admin', 'label_key': 'admin_dashboard', 'url': url_for('admin.dashboard'), 'icon': 'bi-speedometer'},
                {'label': 'Manage Users', 'label_key': 'admin_manage_users', 'icon': 'bi-people'}
            ],
            
            # Business module
            'business.view_data': [
                {'label': 'Business Data', 'label_key': 'business_data', 'icon': 'bi-bar-chart'}
            ],
            
            # Subscription module
            'subscribe_bp.subscribe': [
                {'label': 'Subscription', 'label_key': 'subscribe_title', 'icon': 'bi-star'}
            ],
            
            # Notifications
            'notifications.index': [
                {'label': 'Notifications', 'label_key': 'general_notifications', 'icon': 'bi-bell'}
            ]
        }
        
        # Get breadcrumb items for current endpoint
        if endpoint in breadcrumb_map:
            breadcrumb_items = breadcrumb_map[endpoint].copy()
            
            # Add URLs for items that don't have them (current page items)
            for item in breadcrumb_items:
                if 'url' not in item:
                    item['url'] = request.url
                else:
                    # Validate existing URLs
                    try:
                        # Test if the URL is valid by trying to build it
                        if item['url'].startswith('url_for'):
                            continue  # Skip validation for url_for calls
                    except (BuildError, Exception):
                        logger.warning(f"Invalid URL in breadcrumb item: {item}")
                        item['url'] = '#'
        
        # Filter breadcrumbs based on user role if needed
        if current_user.is_authenticated:
            user_role = getattr(current_user, 'role', 'trader')
            
            # Remove startup-specific breadcrumbs for non-startup users
            if user_role != 'startup' and user_role != 'admin':
                startup_endpoints = ['funds', 'forecasts', 'investor_reports']
                breadcrumb_items = [item for item in breadcrumb_items 
                                  if not any(se in item.get('label_key', '') for se in startup_endpoints)]
            
            # Remove admin-specific breadcrumbs for non-admin users
            if user_role != 'admin':
                admin_endpoints = ['admin']
                breadcrumb_items = [item for item in breadcrumb_items 
                                  if not any(ae in item.get('label_key', '') for ae in admin_endpoints)]
        
        return breadcrumb_items
        
    except Exception as e:
        logger.error(f"Error generating breadcrumb items: {str(e)}")
        return []

def get_page_title():
    """
    Generate page title based on current route and breadcrumb items.
    """
    try:
        breadcrumb_items = get_breadcrumb_items()
        if breadcrumb_items:
            # Use the last breadcrumb item as the page title
            return breadcrumb_items[-1].get('label', 'FiCore Africa')
        return 'FiCore Africa'
    except Exception as e:
        logger.error(f"Error generating page title: {str(e)}")

        return 'FiCore Africa'
