from django import template

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divide value by arg."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def add_filter(value, arg):
    """Add arg to value."""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def get_lat(location):
    """Extract latitude from GeoJSON Point location."""
    try:
        if isinstance(location, dict):
            coords = location.get('coordinates', [0, 0])
            return round(coords[1], 6) if len(coords) > 1 else 0
        return 0
    except (ValueError, TypeError, KeyError):
        return 0


@register.filter
def get_lon(location):
    """Extract longitude from GeoJSON Point location."""
    try:
        if isinstance(location, dict):
            coords = location.get('coordinates', [0, 0])
            return round(coords[0], 6) if len(coords) > 0 else 0
        return 0
    except (ValueError, TypeError, KeyError):
        return 0


@register.filter
def format_coords(location):
    """Format location as 'Lat, Lon' string."""
    try:
        if isinstance(location, dict):
            coords = location.get('coordinates', [0, 0])
            if len(coords) >= 2:
                return f"{coords[1]:.4f}, {coords[0]:.4f}"
        return "Unknown"
    except (ValueError, TypeError, KeyError):
        return "Unknown"