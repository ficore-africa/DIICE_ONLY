from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from translations import trans
import utils
from datetime import datetime, timezone

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

class InventoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    cost = FloatField('Cost', validators=[DataRequired(), NumberRange(min=0)])
    expected_margin = FloatField('Expected Margin', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Item')

@inventory_bp.route('/')
@login_required
def index():
    db = utils.get_mongo_db()
    user_id = str(current_user.id)
    inventory_items = list(db.records.find({'user_id': user_id, 'type': 'inventory'}))
    return render_template('inventory/index.html', inventory_items=inventory_items)

@inventory_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = InventoryForm()
    try:
        can_interact = utils.can_user_interact(current_user)  # Updated to use can_user_interact
    except AttributeError:
        flash(trans('server_error', default='Server configuration error. Please contact support.'), 'error')
        return render_template('inventory/add.html', form=form, can_interact=False)
    
    if form.validate_on_submit() and can_interact:
        try:
            db = utils.get_mongo_db()
            user_id = str(current_user.id)
            db.records.insert_one({
                'user_id': user_id,
                'type': 'inventory',
                'name': form.name.data,
                'cost': form.cost.data,
                'expected_margin': form.expected_margin.data,
                'created_at': datetime.now(timezone.utc)
            })
            flash(trans('inventory_added', default='Inventory item added!'), 'success')
            return redirect(url_for('inventory.index'))
        except Exception as e:
            flash(trans('db_error', default=f'Error adding item: {str(e)}'), 'error')
            return render_template('inventory/add.html', form=form, can_interact=can_interact)
    
    return render_template('inventory/add.html', form=form, can_interact=can_interact)
