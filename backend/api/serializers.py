
from rest_framework import serializers
from .models import Category, Product, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "image",
            "is_active",
        ]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image",
            "is_available",
            "category",
            "category_name",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "price",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    courier_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_name",
            "phone",
            "address",
            "payment_method",
            "total_price",
            "status",
            "items",
            "created_at",
            "courier",
            "courier_name",
            "customer_latitude",
            "customer_longitude",
            "courier_latitude",
            "courier_longitude",
        ]

        read_only_fields = [
            "id",
            "total_price",
            "status",
            "items",
            "created_at",
            "courier",
            "courier_name",
            "customer_latitude",
            "customer_longitude",
            "courier_latitude",
            "courier_longitude",
        ]

    def get_courier_name(self, obj):
        courier = obj.courier

        if courier is None:
            return None

        return courier.get_full_name() or courier.username