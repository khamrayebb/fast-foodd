from django.urls import path

from .views import (
    home,
    categories,
    products,
    create_order,
    admin_login,
    admin_products,
    admin_product_detail,
    admin_couriers,
    admin_courier_detail,
    courier_login,
    courier_orders,
    courier_update_order_status,
    admin_orders,assign_order_to_courier,
    update_courier_location,
    update_customer_location


)

urlpatterns = [
    path("", home),
    path("categories/", categories),
    path("products/", products),
    path("orders/", create_order),

    path("admin-login/", admin_login),

    path("admin/products/", admin_products),
    path(
        "admin/products/<int:pk>/",
        admin_product_detail,
    ),

    path("admin/couriers/", admin_couriers),
    path(
        "admin/couriers/<int:pk>/",
        admin_courier_detail,
    ),
    path("courier-login/", courier_login),
    path("courier/orders/", courier_orders),
    path(
        "courier/orders/<int:pk>/status/",
        courier_update_order_status,
    ),
    path("admin/orders/", admin_orders),
    path(
    "admin/orders/<int:order_id>/assign/",
    assign_order_to_courier,
),
path(
    "courier/orders/<int:order_id>/location/",
    update_courier_location,
),
path(
    "orders/<int:order_id>/customer-location/",
    update_customer_location,
),
]