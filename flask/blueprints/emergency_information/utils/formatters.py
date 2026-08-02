"""
Display formatters for Emergency Information data.
Used in templates and public views.
"""

from datetime import datetime


def format_date(value, fmt='%d %B %Y') -> str:
    """Format a date object or ISO string for display."""
    if value is None:
        return '—'
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def format_gender(value: str) -> str:
    mapping = {
        'male':             'Male',
        'female':           'Female',
        'other':            'Other',
        'prefer_not_to_say': 'Prefer not to say',
    }
    return mapping.get(value, value or '—')


def format_boolean_yn(value: bool) -> str:
    return 'Yes' if value else 'No'


def format_height(value) -> str:
    if value is None:
        return '—'
    return f'{value} cm'


def format_weight(value) -> str:
    if value is None:
        return '—'
    return f'{value} kg'


def format_blood_type(value: str) -> str:
    return value if value else '—'


def format_text_list(value: str) -> list:
    """
    Split a comma/newline-separated text field into a clean list.
    Useful for allergies, conditions, medications.
    """
    if not value:
        return []
    # Split on newlines first, then commas
    import re
    items = re.split(r'[\n,]+', value)
    return [item.strip() for item in items if item.strip()]


def register_template_filters(app):
    """Register all formatters as Jinja2 template filters."""
    app.jinja_env.filters['format_date']       = format_date
    app.jinja_env.filters['format_gender']     = format_gender
    app.jinja_env.filters['format_yn']         = format_boolean_yn
    app.jinja_env.filters['format_height']     = format_height
    app.jinja_env.filters['format_weight']     = format_weight
    app.jinja_env.filters['format_blood_type'] = format_blood_type
    app.jinja_env.filters['format_text_list']  = format_text_list
