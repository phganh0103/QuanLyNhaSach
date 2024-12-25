from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, abort
def role_required(roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.account_role.value not in roles:
                return abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator