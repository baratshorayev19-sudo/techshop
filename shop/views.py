from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from urllib.error import URLError
from urllib.parse import parse_qsl, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import base64
import difflib
import json
import random
from datetime import datetime

from .context_processors import current_language
from .data import PRODUCTS, category_labels, format_price, get_product, localize_product, localize_products, price_to_usd
from .forms import CheckoutForm, ReviewForm
from .models import Order, OrderItem


def _favorite_slugs(request):
    return set(request.session.get("favorites", []))


def _compare_slugs(request):
    return request.session.get("compare", [])


def _stock_status(product, language):
    if product["id"] % 11 == 0:
        quantity = 0
    else:
        quantity = (product["id"] * 7) % 16 + 1
    if quantity == 0:
        label = "Mavjud emas" if language == "uz" else "Out of stock"
        level = "out"
    elif quantity <= 5:
        label = "Kam qoldi" if language == "uz" else "Low stock"
        level = "low"
    else:
        label = "Mavjud" if language == "uz" else "In stock"
        level = "in"
    return {"quantity": quantity, "label": label, "level": level, "is_available": quantity > 0}


def _normalize_search_text(value):
    text = str(value or "").lower()
    for char in "-_/.,:;()[]{}'\"`+&":
        text = text.replace(char, " ")
    return " ".join(text.split())


def _search_text(product, language):
    localized = localize_product(product, language)
    parts = [
        product.get("name", ""),
        product.get("brand", ""),
        product.get("short", ""),
        product.get("category", ""),
        localized.get("name", ""),
        localized.get("category_label", ""),
        localized.get("description", ""),
    ]
    parts.extend(product.get("specs", []))
    return _normalize_search_text(" ".join(str(part) for part in parts if part))


def _matches_smart_search(product, query, language):
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return True

    haystack = _search_text(product, language)
    if normalized_query in haystack:
        return True

    query_words = normalized_query.split()
    haystack_words = haystack.split()
    if not haystack_words:
        return False

    matched_words = 0
    for word in query_words:
        if len(word) <= 2:
            if any(item.startswith(word) for item in haystack_words):
                matched_words += 1
            continue
        if any(word in item or (len(item) > 2 and item in word) for item in haystack_words):
            matched_words += 1
            continue
        close = any(
            item[0] == word[0]
            and abs(len(item) - len(word)) <= 2
            and difflib.SequenceMatcher(None, word, item).ratio() >= 0.76
            for item in haystack_words
            if item
        )
        if close:
            matched_words += 1

    needed_matches = len(query_words) if len(query_words) <= 2 else len(query_words) - 1
    if matched_words and matched_words >= needed_matches:
        return True

    return False


def _attach_product_state(localized, source, language, request):
    localized["is_favorite"] = localized["slug"] in _favorite_slugs(request)
    localized["is_compared"] = localized["slug"] in set(_compare_slugs(request))
    localized["stock"] = _stock_status(source, language)
    return localized


def _with_favorite_flags(products, language, request):
    localized = localize_products(products, language)
    for source, product in zip(products, localized):
        _attach_product_state(product, source, language, request)
    return localized


def _with_favorite_flag(product, language, request):
    localized = localize_product(product, language)
    return _attach_product_state(localized, product, language, request)


def _cart_items(request):
    language = current_language(request)
    cart = request.session.get("cart", {})
    items = []
    total = 0
    old_total = 0
    discount_total = 0
    for slug, quantity in cart.items():
        product = get_product(slug)
        if not product:
            continue
        subtotal = product["price"] * quantity
        old_subtotal = product["old_price"] * quantity
        discount = max(0, old_subtotal - subtotal)
        items.append(
            {
                "product": localize_product(product, language),
                "quantity": quantity,
                "subtotal": subtotal,
                "subtotal_display": format_price(subtotal, language),
                "old_subtotal": old_subtotal,
                "old_subtotal_display": format_price(old_subtotal, language),
                "discount": discount,
                "discount_display": format_price(discount, language),
            }
        )
        total += subtotal
        old_total += old_subtotal
        discount_total += discount
    return {
        "items": items,
        "total": total,
        "old_total": old_total,
        "discount_total": discount_total,
        "total_display": format_price(total, language),
        "old_total_display": format_price(old_total, language),
        "discount_total_display": format_price(discount_total, language),
    }


def _parse_quantity(value, default=1, minimum=1, maximum=10):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        quantity = default
    return min(maximum, max(minimum, quantity))


def home(request):
    language = current_language(request)
    featured = [product for product in PRODUCTS if product["featured"]]
    return render(
        request,
        "shop/home.html",
        {"featured": _with_favorite_flags(featured, language, request), "products": _with_favorite_flags(PRODUCTS, language, request)},
    )


def products(request):
    language = current_language(request)
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "all")
    max_price = request.GET.get("max_price", "")
    sort = request.GET.get("sort", "featured")
    filtered = PRODUCTS

    if category != "all":
        filtered = [product for product in filtered if product["category"] == category]
    if query:
        filtered = [product for product in filtered if _matches_smart_search(product, query, language)]
    if max_price:
        try:
            max_price_usd = price_to_usd(int(max_price.replace(" ", "")), language)
            filtered = [product for product in filtered if product["price"] <= max_price_usd]
        except ValueError:
            pass

    sorters = {
        "price_asc": lambda item: item["price"],
        "price_desc": lambda item: -item["price"],
        "rating": lambda item: -item["rating"],
    }
    if sort in sorters:
        filtered = sorted(filtered, key=sorters[sort])

    return render(
        request,
        "shop/products.html",
        {
            "products": _with_favorite_flags(filtered, language, request),
            "categories": category_labels(language),
            "active_category": category,
            "query": request.GET.get("q", ""),
            "max_price": max_price,
            "sort": sort,
        },
    )


def product_detail(request, slug):
    language = current_language(request)
    product = get_product(slug)
    if not product:
        messages.error(request, "Mahsulot topilmadi." if language == "uz" else "Product not found.")
        return redirect("shop:products")

    all_reviews = request.session.get("product_reviews", {})
    product_reviews = all_reviews.get(slug, [])
    review_form = ReviewForm(language=language)

    if request.method == "POST":
        review_form = ReviewForm(request.POST, language=language)
        if review_form.is_valid():
            review = {
                "name": review_form.cleaned_data["name"],
                "rating": review_form.cleaned_data["rating"],
                "text": review_form.cleaned_data["text"],
            }
            product_reviews = [review] + product_reviews
            all_reviews[slug] = product_reviews
            request.session["product_reviews"] = all_reviews
            request.session.modified = True
            messages.success(request, "Sharhingiz qo'shildi." if language == "uz" else "Your review was added.")
            return redirect("shop:product_detail", slug=slug)

    recently_viewed = [item for item in request.session.get("recently_viewed", []) if item != slug]
    recently_viewed.insert(0, slug)
    request.session["recently_viewed"] = recently_viewed[:8]
    request.session.modified = True

    related = [item for item in PRODUCTS if item["category"] == product["category"] and item["slug"] != slug]
    if len(related) < 4:
        related_slugs = {item["slug"] for item in related}
        related.extend(
            item
            for item in PRODUCTS
            if item["slug"] != slug and item["slug"] not in related_slugs
        )
    related = related[:4]
    recent_products = [get_product(item_slug) for item_slug in recently_viewed[1:5]]
    recent_products = [item for item in recent_products if item]
    return render(
        request,
        "shop/product_detail.html",
        {
            "product": _with_favorite_flag(product, language, request),
            "related": _with_favorite_flags(related, language, request),
            "review_form": review_form,
            "product_reviews": product_reviews,
            "visible_review_count": product["reviews"] + len(product_reviews),
            "recently_viewed": _with_favorite_flags(recent_products, language, request),
        },
    )


def cart(request):
    cart_data = _cart_items(request)
    return render(request, "shop/cart.html", cart_data)


def favorites(request):
    language = current_language(request)
    favorite_order = request.session.get("favorites", [])
    favorite_set = set(favorite_order)
    products = [product for product in PRODUCTS if product["slug"] in favorite_set]
    products.sort(key=lambda product: favorite_order.index(product["slug"]) if product["slug"] in favorite_order else 9999)
    return render(request, "shop/favorites.html", {"products": _with_favorite_flags(products, language, request)})


def compare(request):
    language = current_language(request)
    compare_order = _compare_slugs(request)
    products = [get_product(slug) for slug in compare_order]
    products = [product for product in products if product]
    return render(request, "shop/compare.html", {"products": _with_favorite_flags(products, language, request)})


@require_POST
def toggle_compare(request, slug):
    language = current_language(request)
    product = get_product(slug)
    if not product:
        messages.error(request, "Mahsulot topilmadi." if language == "uz" else "Product not found.")
        return redirect("shop:products")

    compare_list = _compare_slugs(request)
    if slug in compare_list:
        compare_list = [item for item in compare_list if item != slug]
        message = "Mahsulot taqqoslashdan olib tashlandi." if language == "uz" else "Product removed from comparison."
    else:
        compare_list = [slug] + compare_list
        compare_list = compare_list[:4]
        message = "Mahsulot taqqoslashga qo'shildi." if language == "uz" else "Product added to comparison."
    request.session["compare"] = compare_list
    request.session.modified = True
    messages.success(request, message)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("shop:compare")
    return redirect(_safe_next_url(request, next_url))


@require_POST
def toggle_favorite(request, slug):
    language = current_language(request)
    product = get_product(slug)
    if not product:
        messages.error(request, "Mahsulot topilmadi." if language == "uz" else "Product not found.")
        return redirect("shop:products")

    favorites = request.session.get("favorites", [])
    if slug in favorites:
        favorites = [item for item in favorites if item != slug]
        is_favorite = False
        message = "Mahsulot saralanganlardan olib tashlandi." if language == "uz" else "Product removed from favorites."
    else:
        favorites.insert(0, slug)
        is_favorite = True
        message = "Mahsulot saralanganlarga qo'shildi." if language == "uz" else "Product added to favorites."
    request.session["favorites"] = favorites
    request.session.modified = True
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "is_favorite": is_favorite, "favorites_count": len(favorites), "message": message})
    messages.success(request, message)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("shop:products")
    return redirect(_safe_next_url(request, next_url))


@require_POST
def add_to_cart(request, slug):
    language = current_language(request)
    product = get_product(slug)
    if not product:
        messages.error(request, "Mahsulot topilmadi." if language == "uz" else "Product not found.")
        return redirect("shop:products")
    if not _stock_status(product, language)["is_available"]:
        messages.error(request, "Bu mahsulot hozir mavjud emas." if language == "uz" else "This product is out of stock.")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("shop:products")
        return redirect(_safe_next_url(request, next_url))
    quantity = _parse_quantity(request.POST.get("quantity"))
    cart = request.session.get("cart", {})
    cart[slug] = cart.get(slug, 0) + quantity
    request.session["cart"] = cart
    if language == "uz":
        messages.success(request, "Mahsulot savatga muvaffaqiyatli qo'shildi", extra_tags="cart-added")
    else:
        messages.success(request, "Product was successfully added to cart", extra_tags="cart-added")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("shop:products")
    return redirect(_safe_next_url(request, next_url))


@require_POST
def update_cart(request, slug):
    cart = request.session.get("cart", {})
    quantity = _parse_quantity(request.POST.get("quantity"), default=1, minimum=0)
    if quantity == 0:
        cart.pop(slug, None)
    else:
        cart[slug] = quantity
    request.session["cart"] = cart
    return redirect("shop:cart")


@require_POST
def remove_from_cart(request, slug):
    cart = request.session.get("cart", {})
    cart.pop(slug, None)
    request.session["cart"] = cart
    return redirect("shop:cart")


def checkout(request):
    language = current_language(request)
    cart_data = _cart_items(request)
    items = cart_data["items"]
    total_display = cart_data["total_display"]
    if not items:
        message = "Savatcha bo'sh. Buyurtmadan oldin mahsulot qo'shing." if language == "uz" else "Your cart is empty. Add products before checkout."
        messages.info(request, message)
        return redirect("shop:products")

    if request.method == "POST":
        form = CheckoutForm(request.POST, language=language)
        if form.is_valid():
            payment_labels = {
                "uz": {
                    "card": "Karta orqali",
                    "cash": "Olinganda to'lov",
                    "transfer": "Muddatli to'lov",
                },
                "en": {
                    "card": "Card payment",
                    "cash": "Pay on delivery",
                    "transfer": "Installment",
                },
            }
            delivery_labels = {
                "uz": {"delivery": "Yetkazib berish", "pickup": "Olib ketish"},
                "en": {"delivery": "Delivery", "pickup": "Pickup"},
            }
            payment_method = form.cleaned_data["payment_method"]
            delivery_method = request.POST.get("delivery_method", "delivery")
            order_number = f"TS-{datetime.now().strftime('%y%m%d')}-{get_random_string(5).upper()}"
            with transaction.atomic():
                order = Order.objects.create(
                    number=order_number,
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    email=form.cleaned_data["email"],
                    city=form.cleaned_data["city"],
                    address=form.cleaned_data["address"],
                    payment_method=payment_method,
                    delivery_method=delivery_method,
                    total=cart_data["total"],
                )
                OrderItem.objects.bulk_create(
                    [
                        OrderItem(
                            order=order,
                            product_slug=item["product"]["slug"],
                            product_name=item["product"]["name"],
                            product_image=item["product"]["image"],
                            unit_price=item["product"]["price"],
                            quantity=item["quantity"],
                            subtotal=item["subtotal"],
                        )
                        for item in items
                    ]
                )
            request.session["last_order"] = {
                "id": order.id,
                "number": order.number,
                "date": order.created_at.strftime("%d.%m.%Y %H:%M"),
                "full_name": form.cleaned_data["full_name"],
                "phone": form.cleaned_data["phone"],
                "email": form.cleaned_data["email"],
                "city": form.cleaned_data["city"],
                "address": form.cleaned_data["address"],
                "payment_method": payment_labels.get(language, payment_labels["en"]).get(payment_method, payment_method),
                "delivery_method": delivery_labels.get(language, delivery_labels["en"]).get(delivery_method, delivery_method),
                "items": [
                    {
                        "name": item["product"]["name"],
                        "image": item["product"]["image"],
                        "quantity": item["quantity"],
                        "subtotal_display": item["subtotal_display"],
                    }
                    for item in items
                ],
                "total_display": total_display,
            }
            request.session["cart"] = {}
            return redirect("shop:order_success")
    else:
        form = CheckoutForm(language=language)

    context = {"form": form}
    context.update(cart_data)
    return render(request, "shop/checkout.html", context)


def order_success(request):
    order = request.session.get("last_order")
    if not order:
        return redirect("shop:products")
    return render(request, "shop/order_success.html", {"order": order})


def _clean_phone(phone):
    allowed = "+0123456789"
    return "".join(char for char in phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "") if char in allowed)


def _safe_next_url(request, url=None):
    fallback = reverse("shop:home")
    candidate = url if url is not None else request.POST.get("next") or request.GET.get("next") or request.get_full_path()
    if url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return fallback


def _without_login_param(url):
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "login"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _with_login_step(url, step):
    clean_url = _without_login_param(url)
    parts = urlsplit(clean_url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("login", step))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _send_sms_code(phone, code):
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
        return False

    payload = urlencode(
        {
            "Body": f"TechShop tasdiqlash kodi: {code}",
            "From": settings.TWILIO_FROM_NUMBER,
            "To": phone,
        }
    ).encode()
    credentials = f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()
    request = Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
        data=payload,
        headers={
            "Authorization": f"Basic {base64.b64encode(credentials).decode()}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urlopen(request, timeout=12) as response:
        return 200 <= response.status < 300


@require_POST
def request_login_code(request):
    language = current_language(request)
    phone = _clean_phone(request.POST.get("phone", ""))
    next_url = _safe_next_url(request)

    if len(phone) < 9:
        messages.error(request, "Telefon raqamni to'g'ri kiriting." if language == "uz" else "Enter a valid phone number.")
        return redirect(_with_login_step(next_url, "phone"))

    code = f"{random.randint(1000, 9999)}"
    request.session["auth_pending_phone"] = phone
    request.session["auth_code"] = code
    try:
        sent = _send_sms_code(phone, code)
    except (URLError, TimeoutError):
        sent = False

    if sent:
        message = "SMS kod telefon raqamingizga yuborildi." if language == "uz" else "SMS code was sent to your phone."
    else:
        message = f"SMS provider sozlanmagan. Demo kod: {code}" if language == "uz" else f"SMS provider is not configured. Demo code: {code}"
    messages.success(request, message)
    return redirect(_with_login_step(next_url, "code"))


@require_POST
def verify_login_code(request):
    language = current_language(request)
    code = request.POST.get("code", "").strip()
    next_url = _safe_next_url(request)

    if code and code == request.session.get("auth_code"):
        request.session["auth_phone"] = request.session.get("auth_pending_phone", "")
        request.session.pop("auth_email", None)
        request.session.pop("auth_name", None)
        request.session.pop("auth_pending_phone", None)
        request.session.pop("auth_code", None)
        messages.success(request, "Muvaffaqiyatli kirdingiz." if language == "uz" else "You are signed in.")
        return redirect(_without_login_param(next_url))

    messages.error(request, "Kod noto'g'ri. Qayta urinib ko'ring." if language == "uz" else "Incorrect code. Try again.")
    return redirect(_with_login_step(next_url, "code"))


def logout_user(request):
    request.session.pop("auth_phone", None)
    request.session.pop("auth_email", None)
    request.session.pop("auth_name", None)
    return redirect(_without_login_param(_safe_next_url(request, request.GET.get("next") or reverse("shop:home"))))


def google_login(request):
    language = current_language(request)
    if not settings.GOOGLE_CLIENT_ID:
        messages.error(
            request,
            "Google akkauntlar oynasi chiqishi uchun .env faylga GOOGLE_CLIENT_ID qo'ying."
            if language == "uz"
            else "Set GOOGLE_CLIENT_ID in .env to show the Google account chooser.",
        )
        return redirect(_with_login_step(_safe_next_url(request), "phone"))

    state = get_random_string(32)
    next_url = _safe_next_url(request, request.GET.get("next"))
    request.session["google_oauth_state"] = state
    request.session["google_oauth_next"] = next_url
    callback_url = request.build_absolute_uri(reverse("shop:google_callback"))
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


def google_callback(request):
    language = current_language(request)
    state = request.GET.get("state", "")
    code = request.GET.get("code", "")
    next_url = _safe_next_url(request, request.session.pop("google_oauth_next", reverse("shop:home")))

    if not code or state != request.session.pop("google_oauth_state", ""):
        messages.error(request, "Google login bekor qilindi." if language == "uz" else "Google login was cancelled.")
        return redirect(_with_login_step(next_url, "phone"))

    if not settings.GOOGLE_CLIENT_SECRET:
        messages.error(
            request,
            "Google loginni yakunlash uchun .env faylga GOOGLE_CLIENT_SECRET qo'ying."
            if language == "uz"
            else "Set GOOGLE_CLIENT_SECRET in .env to finish Google sign-in.",
        )
        return redirect(_with_login_step(next_url, "phone"))

    callback_url = request.build_absolute_uri(reverse("shop:google_callback"))
    token_payload = urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": callback_url,
            "grant_type": "authorization_code",
        }
    ).encode()

    try:
        token_request = Request(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(token_request, timeout=10) as response:
            token_data = json.loads(response.read().decode())

        user_request = Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        with urlopen(user_request, timeout=10) as response:
            profile = json.loads(response.read().decode())
    except (KeyError, URLError, TimeoutError, json.JSONDecodeError):
        messages.error(request, "Google orqali kirishda xatolik bo'ldi." if language == "uz" else "Google sign-in failed.")
        return redirect(_with_login_step(next_url, "phone"))

    email = profile.get("email", "")
    if not email:
        messages.error(request, "Google email topilmadi." if language == "uz" else "Google email was not found.")
        return redirect(_with_login_step(next_url, "phone"))

    request.session["auth_email"] = email
    request.session["auth_name"] = profile.get("name") or email
    request.session.pop("auth_phone", None)
    request.session.pop("auth_pending_phone", None)
    request.session.pop("auth_code", None)
    messages.success(request, "Google orqali muvaffaqiyatli kirdingiz." if language == "uz" else "Signed in with Google.")
    return redirect(_without_login_param(next_url))


def login_page(request):
    next_url = request.GET.get("next") or request.get_full_path()
    return render(
        request,
        "shop/login.html",
        {"next_url": _safe_next_url(request, next_url), "is_login_page": True},
    )


def about(request):
    return render(request, "shop/about.html")


def contact(request):
    return render(request, "shop/contact.html")
