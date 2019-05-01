
from functools import wraps
from flask import current_app  # request
from flask_login import current_user  # login_fresh


def role_required(required='ADMIN'):
    def decorator(func):
        @wraps(func)
        def wrapper(*arg, **kwargs):
            if current_user.is_permission(required):
                return func(*arg, **kwargs)
            return current_app.login_manager.unauthorized()
        return wrapper
    return decorator


# from flask_login
# def login_required(func):
#     @wraps(func)
#     def decorated_view(*args, **kwargs):
#         if request.method in ['OPTIONS']:
#             return func(*args, **kwargs)
#         elif current_app.login_manager._login_disabled:
#             return func(*args, **kwargs)
#         elif not current_user.is_authenticated:
#             return current_app.login_manager.unauthorized()
#         elif not login_fresh():
#             return current_app.login_manager.needs_refresh()
#         return func(*args, **kwargs)
#     return decorated_view
