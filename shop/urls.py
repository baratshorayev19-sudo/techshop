from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("favorites/", views.favorites, name="favorites"),
    path("favorites/toggle/<slug:slug>/", views.toggle_favorite, name="toggle_favorite"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<slug:slug>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<slug:slug>/", views.update_cart, name="update_cart"),
    path("cart/remove/<slug:slug>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/success/", views.order_success, name="order_success"),
    path("login/", views.login_page, name="login"),
    path("login/request-code/", views.request_login_code, name="request_login_code"),
    path("login/verify-code/", views.verify_login_code, name="verify_login_code"),
    path("login/google/", views.google_login, name="google_login"),
    path("login/google/callback/", views.google_callback, name="google_callback"),
    path("logout/", views.logout_user, name="logout"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
