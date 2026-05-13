from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_slug", "product_name", "product_image", "unit_price", "quantity", "subtotal")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "full_name", "phone", "city", "total", "status", "created_at")
    list_filter = ("status", "payment_method", "delivery_method", "created_at")
    search_fields = ("number", "full_name", "phone", "email", "city")
    readonly_fields = ("number", "created_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "quantity", "unit_price", "subtotal")
    search_fields = ("product_name", "product_slug", "order__number")
