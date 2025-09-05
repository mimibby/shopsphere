from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
import logging
from django.db import transaction

from .models import (
    Product, Category, Order, OrderItem, Review, Wishlist, HeroImage, OrderTracking
)
from .forms import ReviewForm

logger = logging.getLogger(__name__)

# -----------------------------
# HOME PAGE
# -----------------------------
def home(request):
    products = Product.objects.all().order_by('-created_at')[:12]
    categories = Category.objects.all()
    hero_images = HeroImage.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        'hero_images': hero_images
    })

# -----------------------------
# ALL PRODUCTS
# -----------------------------
def all_products(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'shop/all_products.html', {
        'products': products,
        'categories': categories
    })

# -----------------------------
# PRODUCT DETAIL
# -----------------------------

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    product_images = product.images.all()
    avg_rating = reviews.aggregate(average_rating=Avg('rating'))['average_rating'] or 0

    # Check if the logged-in user purchased this product
    purchased = False
    if request.user.is_authenticated:
        purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status='Delivered',  # only allows reviews after delivery
            product=product
        ).exists()

    # Prepare review form
    form = ReviewForm()

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'product_images': product_images,
        'avg_rating': avg_rating,
        'purchased': purchased,
        'form': form,
    })

# -----------------------------
# CATEGORY PRODUCTS
# -----------------------------
def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category).order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'shop/category.html', {
        'category': category,
        'products': products,
        'categories': categories
    })

# -----------------------------
# CART HELPERS
# -----------------------------
def get_cart_items(request):
    cart = request.session.get('cart', {})
    items, total = [], 0
    for pid, qty in cart.items():
        try:
            product = Product.objects.get(id=int(pid))
            subtotal = product.price * qty
            items.append({'product': product, 'quantity': qty, 'subtotal': subtotal})
            total += subtotal
        except Product.DoesNotExist:
            continue
    return items, total

# -----------------------------
# CART VIEWS
# -----------------------------
@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        quantity = int(request.POST.get('quantity', 1))
        cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
        request.session['cart'] = cart
        messages.success(request, "Item added to cart.")
    return redirect('shop:product_detail', product_id=product_id)

@login_required
def remove_from_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        cart.pop(str(product_id), None)
        request.session['cart'] = cart
        messages.success(request, "Item removed from cart.")
    return redirect('shop:cart')

@login_required
def cart(request):
    items, total = get_cart_items(request)
    return render(request, 'shop/cart.html', {'cart_items': items, 'total': total})

@login_required
@csrf_exempt
def update_cart(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        for key, val in request.POST.items():
            if key.startswith('quantities_'):
                pid = key.replace('quantities_', '')
                try:
                    qty = int(val)
                    if qty > 0:
                        cart[pid] = qty
                    else:
                        cart.pop(pid, None)
                except ValueError:
                    continue
        request.session['cart'] = cart
        messages.success(request, "Cart updated.")
    return redirect('shop:cart')

# -----------------------------
# CHECKOUT
# -----------------------------
@login_required
def checkout(request):
    items, total = get_cart_items(request)
    return render(request, 'shop/checkout.html', {'cart_items': items, 'total': total})

# -----------------------------
# PLACE ORDER
# -----------------------------
@login_required
def place_order(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if not cart:
            messages.error(request, "Your cart is empty.")
            return redirect('shop:checkout')

        try:
            with transaction.atomic():
                # Creates order with initial total 0
                order = Order.objects.create(user=request.user, total_price=0)
                order_items = []
                total = 0

                # Creates order items
                for pid, qty in cart.items():
                    product = Product.objects.select_for_update().get(id=pid)  
                    subtotal = product.price * qty
                    total += subtotal
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=qty,
                        price=product.price
                    )
                    order_items.append(order_item)

                # Updates order total
                order.total_price = total
                order.save()

                # Creates first tracking record
                OrderTracking.objects.create(order=order, status="Processing")

                # Clears session cart
                request.session['cart'] = {}

            # Sends confirmation email outside the transaction (to avoid rollback if email fails)
            try:
                items_text = "\n".join([f"{i.product.name} x{i.quantity} - ₦{i.price*i.quantity}" for i in order_items])
                send_mail(
                    subject=f"Order #{order.id} Confirmation",
                    message=f"Hi {request.user.username},\n\nYour order summary:\n{items_text}\nTotal: ₦{total}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.warning(f"Failed to send order email: {e}")

            return redirect('shop:order_success')

        except Product.DoesNotExist:
            messages.error(request, "One of the products in your cart was not found.")
            return redirect('shop:checkout')
        except Exception as e:
            logger.exception(f"Order placement failed: {e}")
            messages.error(request, "Something went wrong while placing your order. Please try again.")
            return redirect('shop:checkout')

    return redirect('shop:checkout')

# -----------------------------
# ORDER SUCCESS
# -----------------------------
@login_required
def order_success(request):
    return render(request, 'shop/order_success.html')

# -----------------------------
# ORDER TRACKING
# -----------------------------
@login_required
def order_tracking_view(request):
    updates = OrderTracking.objects.filter(order__user=request.user).select_related('order').order_by('-updated_at')
    return render(request, 'shop/order_tracking.html', {'tracking_updates': updates})

@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    tracking_updates = OrderTracking.objects.filter(order=order).order_by('-updated_at')
    return render(request, 'shop/track_order.html', {
        'order': order,
        'tracking_updates': tracking_updates
    })

# -----------------------------
# ORDER HISTORY
# -----------------------------
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(orders, 5)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    reviewed_products = Review.objects.filter(user=request.user).values_list('product_id', flat=True)
    review_form = ReviewForm()
    return render(request, 'shop/order_history.html', {
        'page_obj': page_obj,
        'review_form': review_form,
        'reviewed_products': reviewed_products
    })

# -----------------------------
# REVIEWS
# -----------------------------
@login_required
def submit_review_from_order(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Review submitted.")
        else:
            messages.error(request, "please check your review details and try again .")
    return redirect('shop:order_history')

@login_required
def user_reviews(request):
    reviews = Review.objects.filter(user=request.user)
    return render(request, 'shop/user_reviews.html', {'reviews': reviews})


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Ensure user purchased the product (and delivered)
    purchased = OrderItem.objects.filter(
        order__user=request.user,
        order__status='Delivered',
        product=product
    ).exists()
    if not purchased:
        return HttpResponseForbidden("You can only review products you have purchased and received.")

    # Prevent duplicate review
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.info(request, "You have already reviewed this product.")
        return redirect('shop:order_history')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Thank you! Your review has been submitted.")
            return redirect('shop:order_history')
        else:
            messages.error(request, "Please check your review details and try again.")
    else:
        # Render the review form on GET
        form = ReviewForm()

    return render(request, 'shop/review_form.html', {'form': form, 'product': product})

# -----------------------------
# WISHLIST
# -----------------------------
@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist.products.add(product)
    return redirect('shop:product_detail', product_id=product.id)

@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist = get_object_or_404(Wishlist, user=request.user)
    wishlist.products.remove(product)
    return redirect('shop:wishlist_view')

@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'shop/wishlist.html', {'products': wishlist.products.all()})

# -----------------------------
# SEARCH
# -----------------------------
def search_results(request):
    query = request.GET.get('q')
    products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)) if query else []
    return render(request, 'shop/search_results.html', {'products': products, 'query': query})

# -----------------------------
# TRACKING EMAIL
# -----------------------------
def send_tracking_update_email(tracking):
    try:
        order = tracking.order
        user = order.user
        context = {'user': user, 'order': order, 'tracking': tracking}
        subject = f"Order #{order.id} Updated"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
        to_email = [user.email]
        text_content = f"Hi {user.username}, your order #{order.id} status is now '{tracking.status}'."
        html_content = render_to_string('store/emails/tracking_update.html', context)
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Failed to send tracking update email for order %s: %s", getattr(tracking.order, 'id', 'unknown'), exc)