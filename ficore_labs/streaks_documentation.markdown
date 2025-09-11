# Streaks System Documentation

## Overview
The streaks system in the application encourages users to maintain consistent daily activity by tracking consecutive days of transactions (e.g., debtors, creditors, funds, receipts, or payments). Streaks are stored in a MongoDB collection and displayed on the rewards and dashboard pages. Users earn points for each active day, which can be redeemed for rewards, such as a 30% subscription discount.

## Functionality
The streaks system is implemented in the `rewards.py` Blueprint, specifically within the `/rewards/` route. Below is a detailed explanation of how streaks are calculated, updated, and managed.

### Streak Calculation
- **Definition**: A streak represents the number of consecutive days a user has recorded at least one transaction in the `records` or `cashflows` MongoDB collections.
- **Data Storage**:
  - Streaks are stored in the `rewards` collection in MongoDB, with the following schema for each document:
    ```json
    {
      "user_id": "<string>",
      "streak": <integer>,
      "points": <integer>,
      "last_activity_date": <ISODate>,
      "updated_at": <ISODate>
    }
    ```
  - `user_id`: Matches the user's ID from the `users` collection.
  - `streak`: The current streak count (number of consecutive active days).
  - `points`: Accumulated points earned for daily activities.
  - `last_activity_date`: Timestamp of the most recent day with a transaction.
  - `updated_at`: Timestamp of the last update to the document.
- **Activity Check**:
  - A day is considered "active" if the user has at least one transaction in the `records` collection (types: `debtor`, `creditor`, `fund`, `receipt`, `payment`) or the `cashflows` collection (types: `receipt`, `payment`) created on that day.
  - The check uses a time window from midnight UTC of the current day (`today_start`) to midnight UTC of the next day (`today_end`).

### Streak Update Logic
The streak is updated when a user visits the `/rewards/` route, based on their transaction activity. The logic is as follows:
1. **Fetch Current Data**:
   - Retrieve the user's rewards document from the `rewards` collection using `db.rewards.find_one({'user_id': user_id})`.
   - Extract `streak`, `points`, and `last_activity_date`. If no document exists, default to `streak = 0`, `points = 0`, and `last_activity_date = None`.
2. **Determine Today's Activity**:
   - Query the `records` and `cashflows` collections to count transactions created today (between `today_start` and `today_end`).
   - If either collection has at least one transaction, set `has_today_activity = True`.
3. **Update Streak and Points**:
   - If `has_today_activity` is `True`:
     - If `last_activity_date` exists:
       - If `last_activity_date` is yesterday (`today - 1 day`), increment `streak` by 1.
       - If `last_activity_date` is before yesterday, reset `streak` to 1 (new streak starts).
       - If `last_activity_date` is today, keep `streak` unchanged (already updated today).
     - If `last_activity_date` is `None`, set `streak` to 1 (first activity).
     - Increment `points` by 1.
     - Update the `rewards` document with the new `streak`, `points`, `last_activity_date` (set to now), and `updated_at` (set to now) using `db.rewards.update_one` with `upsert=True`.
   - If `has_today_activity` is `False` and `last_activity_date` is before yesterday:
     - Reset `streak` to 0.
     - Update the `rewards` document with `streak = 0` and `updated_at` set to now.
4. **Database Operation**:
   - The update uses MongoDB's `update_one` with `$set` to modify fields and `upsert=True` to create a new document if none exists.
   - Example update query for an active day:
     ```python
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
     ```

### Reward Redemption
- **Eligibility**: Users can redeem a 30% discount on their next subscription if they have at least 100 points and have not already redeemed a discount (`discount_applied = False` in the `users` collection).
- **Redemption Process**:
  - Handled by the `/rewards/redeem` POST route.
  - Checks if `points >= 100` and `discount_applied` is `False`.
  - If eligible:
    - Updates the `users` collection to set `discount_applied = True`, `discount_percentage = 30`, and `discount_expiry` to 30 days from now.
    - Deducts 100 points from the `rewards` document using `$inc: {'points': -100}`.
    - Flashes a success message.
  - If ineligible, flashes a warning message (e.g., insufficient points or discount already applied).

### Display
- **Rewards Page** (`rewards/index.html`):
  - Displays the current `streak` and `points` in Bootstrap cards.
  - Shows a badge (`Keep it up!`) if `streak >= 3`.
  - Provides a form to redeem points if `can_redeem` is `True`, or displays appropriate messages if `discount_applied` is `True` or points are insufficient.
  - Includes a tips section explaining how to earn and maintain streaks.
- **Dashboard Page** (`dashboard/index.html`):
  - Displays the `streak` in a card with a badge for `streak >= 3`, linking to the rewards page.

### Error Handling
- **Database Errors**:
  - Wrapped in a `try-except` block in the `/rewards/` route.
  - Logs errors with `logger.error`, including `user_id`, `session_id`, and `ip_address`.
  - Flashes a user-friendly error message and redirects to the dashboard.
  - Example:
    ```python
    except Exception as e:
        logger.error(f"Error loading rewards for user {user_id}: {str(e)}",
                     extra={'session_id': session.get('sid', 'no-session-id'), 'ip_address': request.remote_addr})
        flash(trans('general_error', default='An error occurred while loading your rewards.'), 'danger')
        return redirect(url_for('dashboard.index'))
    ```
- **Session Issues**:
  - If `session.get('sid')` returns `None`, logs `no-session-id` to track potential session configuration issues.
  - Ensure `app.config['SECRET_KEY']` is set and session storage (e.g., Flask-Session or Redis) is configured.
- **Timezone Handling**:
  - Uses `datetime.now(timezone.utc)` for consistency.
  - Strips time components (hour, minute, second, microsecond) from `last_activity_date` and `today` for day-based comparisons.

## Dependencies
- **Flask Modules**:
  - `Blueprint`, `render_template`, `flash`, `redirect`, `url_for`, `session`, `request` from `flask`.
  - `login_required`, `current_user` from `flask_login`.
- **MongoDB**:
  - Uses `pymongo` via `utils.get_mongo_db()` to access the `rewards`, `records`, `cashflows`, and `users` collections.
  - Requires `bson.ObjectId` for user ID handling.
- **Other**:
  - `datetime`, `timedelta`, `timezone` from `datetime` for date calculations.
  - `logger` from `utils` for error logging.
  - `trans` from `translations` for internationalization.

## Implementation Notes
- **Consistency**:
  - The streak is fetched from the `rewards` collection in both `/rewards/` and `/dashboard/` routes to ensure a single source of truth.
  - The `dashboard/routes.py` route was updated to query `db.rewards` directly, aligning with `rewards.py`.
- **Performance**:
  - Queries for today’s transactions (`records` and `cashflows`) are optimized with time-based filters.
  - Consider adding indexes on `records.created_at` and `cashflows.created_at` for large datasets:
    ```python
    db.records.create_index([("created_at", 1), ("user_id", 1), ("type", 1)])
    db.cashflows.create_index([("created_at", 1), ("user_id", 1), ("type", 1)])
    ```
- **Security**:
  - Uses `@login_required` to restrict access to authenticated users.
  - CSRF protection is included in the redemption form via `csrf_token()`.
- **Testing**:
  - Test streak updates by creating transactions on consecutive days and verifying `streak` increments.
  - Test streak reset by skipping a day and checking that `streak` becomes 0.
  - Test redemption with sufficient points and verify `discount_applied` and `points` updates.
  - Simulate database errors to ensure proper error handling and user redirection.

## Future Improvements
- **Granular Activity Tracking**:
  - Track specific transaction types for more detailed streak criteria (e.g., only sales count).
- **Notifications**:
  - Add reminders for users to maintain their streak via email or in-app notifications.
- **Advanced Rewards**:
  - Introduce tiered rewards (e.g., different discounts for higher point thresholds).
- **Caching**:
  - Cache streak data in Redis to reduce MongoDB queries for high-traffic users.