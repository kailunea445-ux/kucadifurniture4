from django.db.models import Sum

def cart_item_count(request):
    """Return total cart items for the logged-in user as `total_cart_items`."""
    total = 0
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        try:
            cart = user.cart
            total = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        except Exception:
            total = 0
    return {'total_cart_items': total}
