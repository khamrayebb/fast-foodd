
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category, Product, Order, OrderItem, UserProfile
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
)


# =========================================================
# UMUMIY YORDAMCHI FUNKSIYALAR
# =========================================================

def is_admin_user(user):
    """Foydalanuvchi admin ekanini tekshirish."""

    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    if user.is_superuser:
        return True

    try:
        profile = user.profile
        return profile.role == "admin" and profile.is_active
    except UserProfile.DoesNotExist:
        return False


def get_user_profile(user):
    """Foydalanuvchining profilini xavfsiz olish."""

    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def error_response(message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=http_status)


# =========================================================
# API HOME
# =========================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def home(request):
    return Response({
        "message": "Fast Food API ishlayapti!",
        "status": "success",
    })


# =========================================================
# KATEGORIYALAR
# =========================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def categories(request):
    queryset = Category.objects.filter(
        is_active=True
    ).order_by("id")

    serializer = CategorySerializer(queryset, many=True)
    return Response(serializer.data)


# =========================================================
# MAHSULOTLAR — FOYDALANUVCHI UCHUN
# =========================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def products(request):
    queryset = (
        Product.objects
        .filter(
            is_available=True,
            category__is_active=True,
        )
        .select_related("category")
        .order_by("-id")
    )

    serializer = ProductSerializer(queryset, many=True)
    return Response(serializer.data)


# =========================================================
# FOYDALANUVCHI BUYURTMASI
# =========================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def create_order(request):
    data = request.data

    customer_name = str(
        data.get("customer_name", "")
    ).strip()

    phone = str(data.get("phone", "")).strip()
    address = str(data.get("address", "")).strip()
    payment_method = data.get("payment_method", "cash")
    items = data.get("items", [])

    if not customer_name:
        return error_response("Ism kiritilishi kerak.")

    if not phone:
        return error_response("Telefon raqam kiritilishi kerak.")

    if not address:
        return error_response("Yetkazib berish manzili kiritilishi kerak.")

    if payment_method not in ["cash", "click", "payme"]:
        return error_response("To'lov turi noto'g'ri.")

    if not isinstance(items, list) or not items:
        return error_response("Savat bo'sh.")

    products_data = []
    total_price = Decimal("0.00")

    # Mahsulotlarni tekshirish
    for item in items:
        if not isinstance(item, dict):
            return error_response("Buyurtma tarkibi noto'g'ri.")

        product_id = item.get("product_id")

        try:
            quantity = int(item.get("quantity", 1))
        except (ValueError, TypeError):
            return error_response("Mahsulot miqdori noto'g'ri.")

        if quantity <= 0:
            return error_response(
                "Mahsulot miqdori 1 yoki undan katta bo'lishi kerak."
            )

        try:
            product = Product.objects.get(
                id=product_id,
                is_available=True,
                category__is_active=True,
            )
        except (Product.DoesNotExist, ValueError, TypeError):
            return error_response(
                f"Mahsulot topilmadi: {product_id}",
                status.HTTP_404_NOT_FOUND,
            )

        price = product.price
        total_price += price * quantity

        products_data.append({
            "product": product,
            "quantity": quantity,
            "price": price,
        })

    # Buyurtma va uning mahsulotlarini bitta tranzaksiyada saqlash
    with transaction.atomic():
        order = Order.objects.create(
            customer_name=customer_name,
            phone=phone,
            address=address,
            payment_method=payment_method,
            total_price=total_price,
            status="new",
        )
        latitude = request.data.get("customer_latitude")
        longitude = request.data.get("customer_longitude")

        if latitude is not None and longitude is not None:
            order.customer_latitude = latitude
            order.customer_longitude = longitude
            order.save(
                update_fields=[
                    "customer_latitude",
                    "customer_longitude",
                ]
            )   

        for item in products_data:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                quantity=item["quantity"],
                price=item["price"],
            )

    order = (
        Order.objects
        .select_related("courier")
        .prefetch_related("items__product")
        .get(pk=order.pk)
    )

    serializer = OrderSerializer(order)

    return Response(
        {
            "message": "Buyurtma muvaffaqiyatli yaratildi.",
            "order": serializer.data,
        },
        status=status.HTTP_201_CREATED,
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def admin_login(request):
    username = str(
        request.data.get("username", "")
    ).strip()

    password = request.data.get("password", "")

    if not username or not password:
        return error_response("Login va parolni kiriting.")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return error_response(
            "Login yoki parol noto'g'ri.",
            status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return error_response(
            "Hisobingiz faol emas.",
            status.HTTP_403_FORBIDDEN,
        )

    if not is_admin_user(user):
        return error_response(
            "Admin paneliga kirish huquqingiz yo'q.",
            status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "Admin tizimga muvaffaqiyatli kirdi.",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
            "role": "admin",
        },
    })


# =========================================================
# ADMIN: MAHSULOTLAR RO'YXATI VA YARATISH
# =========================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin_products(request):
    if not is_admin_user(request.user):
        return error_response(
            "Admin huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        queryset = (
            Product.objects
            .select_related("category")
            .order_by("-id")
        )

        serializer = ProductSerializer(queryset, many=True)
        return Response(serializer.data)

    serializer = ProductSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


# =========================================================
# ADMIN: MAHSULOTNI TAHRIRLASH VA O'CHIRISH
# =========================================================

@api_view(["PATCH", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def admin_product_detail(request, pk):
    if not is_admin_user(request.user):
        return error_response(
            "Admin huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return error_response(
            "Mahsulot topilmadi.",
            status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        product.delete()
        return Response({
            "message": "Mahsulot o'chirildi."
        })

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=(request.method == "PATCH"),
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


# =========================================================
# ADMIN: KURYERLARNI KO'RISH VA YARATISH
# =========================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin_couriers(request):
    if not is_admin_user(request.user):
        return error_response(
            "Admin huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    # Kuryerlar ro'yxati
    if request.method == "GET":
        profiles = (
            UserProfile.objects
            .filter(role="courier")
            .select_related("user")
            .order_by("-id")
        )

        data = [
            {
                # id — aynan Django User ID.
                # Frontend biriktirish uchun shu qiymatni yuboradi.
                "id": profile.user.id,
                "user_id": profile.user.id,
                "profile_id": profile.id,
                "username": profile.user.username,
                "first_name": profile.user.first_name,
                "phone": profile.phone,
                "is_active": (
                    profile.is_active
                    and profile.user.is_active
                ),
                "role": profile.role,
                "created_at": profile.created_at,
            }
            for profile in profiles
        ]

        return Response(data)

    # Yangi kuryer yaratish
    username = str(
        request.data.get("username", "")
    ).strip()

    password = request.data.get("password", "")

    first_name = str(
        request.data.get("first_name", "")
    ).strip()

    phone = str(
        request.data.get("phone", "")
    ).strip()

    if not username or not password:
        return error_response("Login va parol majburiy.")

    if len(password) < 8:
        return error_response(
            "Parol kamida 8 ta belgidan iborat bo'lishi kerak."
        )

    if User.objects.filter(username=username).exists():
        return error_response("Bu login band.")

    with transaction.atomic():
        courier = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
        )

        profile = UserProfile.objects.create(
            user=courier,
            role="courier",
            phone=phone,
            is_active=True,
        )

    return Response(
        {
            "message": "Kuryer muvaffaqiyatli yaratildi.",
            "courier": {
                "id": courier.id,
                "user_id": courier.id,
                "profile_id": profile.id,
                "username": courier.username,
                "first_name": courier.first_name,
                "phone": profile.phone,
                "is_active": True,
                "role": "courier",
            },
        },
        status=status.HTTP_201_CREATED,
    )


# =========================================================
# ADMIN: KURYER HOLATINI O'ZGARTIRISH
# =========================================================

@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def admin_courier_detail(request, pk):
    if not is_admin_user(request.user):
        return error_response(
            "Admin huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    # pk bu yerda User.id hisoblanadi.
    # Shuning uchun admin_couriers qaytargan id bilan mos.
    try:
        profile = (
            UserProfile.objects
            .select_related("user")
            .get(user_id=pk, role="courier")
        )
    except UserProfile.DoesNotExist:
        return error_response(
            "Kuryer topilmadi.",
            status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        profile.is_active = False
        profile.user.is_active = False

        profile.save(update_fields=["is_active"])
        profile.user.save(update_fields=["is_active"])

        return Response({
            "message": "Kuryer hisobi faolsizlantirildi."
        })

    active = request.data.get("is_active")

    if not isinstance(active, bool):
        return error_response(
            "is_active true yoki false bo'lishi kerak."
        )

    profile.is_active = active
    profile.user.is_active = active

    profile.save(update_fields=["is_active"])
    profile.user.save(update_fields=["is_active"])

    return Response({
        "message": "Kuryer holati yangilandi.",
        "id": profile.user.id,
        "profile_id": profile.id,
        "is_active": active,
    })


# =========================================================
# KURYER LOGIN
# =========================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def courier_login(request):
    username = str(
        request.data.get("username", "")
    ).strip()

    password = request.data.get("password", "")

    if not username or not password:
        return error_response("Login va parolni kiriting.")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None or not user.is_active:
        return error_response(
            "Login yoki parol noto'g'ri.",
            status.HTTP_401_UNAUTHORIZED,
        )

    profile = get_user_profile(user)

    if profile is None:
        return error_response(
            "Kuryer profili topilmadi.",
            status.HTTP_403_FORBIDDEN,
        )

    if profile.role != "courier" or not profile.is_active:
        return error_response(
            "Kuryer hisobiga kirish huquqi yo'q.",
            status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "Kuryer tizimga kirdi.",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "role": "courier",
        },
    })


# =========================================================
# KURYER: O'ZIGA BIRIKTIRILGAN BUYURTMALAR
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courier_orders(request):
    profile = get_user_profile(request.user)

    if (
        profile is None
        or profile.role != "courier"
        or not profile.is_active
        or not request.user.is_active
    ):
        return error_response(
            "Kuryer huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    orders = (
        Order.objects
        .filter(courier=request.user)
        .select_related("courier")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


# =========================================================
# KURYER: BUYURTMA HOLATINI O'ZGARTIRISH
# =========================================================

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def courier_update_order_status(request, pk):
    profile = get_user_profile(request.user)

    if (
        profile is None
        or profile.role != "courier"
        or not profile.is_active
        or not request.user.is_active
    ):
        return error_response(
            "Kuryer huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    try:
        order = Order.objects.get(
            pk=pk,
            courier=request.user,
        )
    except Order.DoesNotExist:
        return error_response(
            "Buyurtma topilmadi yoki sizga biriktirilmagan.",
            status.HTTP_404_NOT_FOUND,
        )

    new_status = request.data.get("status")

    allowed_transitions = {
        "confirmed": {"delivering"},
        "ready": {"delivering"},
        "delivering": {"delivered"},
    }

    allowed_next = allowed_transitions.get(order.status, set())

    if new_status not in allowed_next:
        return error_response(
            "Bu holatga o'tishga ruxsat berilmagan."
        )

    order.status = new_status
    order.save(update_fields=["status"])

    return Response({
        "message": "Buyurtma holati yangilandi.",
        "order_id": order.id,
        "status": order.status,
    })


# =========================================================
# ADMIN: BUYURTMALAR RO'YXATI
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_orders(request):
    if not is_admin_user(request.user):
        return error_response(
            "Admin huquqi talab qilinadi.",
            status.HTTP_403_FORBIDDEN,
        )

    orders = (
        Order.objects
        .select_related("courier")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


# =========================================================
# ADMIN: BUYURTMANI KURYERGA BIRIKTIRISH
# =========================================================

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def assign_order_to_courier(request, order_id):
    if not is_admin_user(request.user):
        return error_response(
            "Faqat admin buyurtmani kuryerga biriktira oladi.",
            status.HTTP_403_FORBIDDEN,
        )

    courier_id = request.data.get("courier_id")

    try:
        courier_id = int(courier_id)

        if courier_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return error_response("Kuryer ID raqami noto'g'ri.")

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return error_response(
            "Buyurtma topilmadi.",
            status.HTTP_404_NOT_FOUND,
        )

    if order.status in ["delivered", "cancelled"]:
        return error_response(
            "Yakunlangan yoki bekor qilingan buyurtmani "
            "biriktirib bo'lmaydi."
        )

    # Frontenddan User.id keladi.
    try:
        profile = (
            UserProfile.objects
            .select_related("user")
            .get(
                user_id=courier_id,
                role="courier",
                is_active=True,
                user__is_active=True,
            )
        )
    except UserProfile.DoesNotExist:
        return error_response(
            "Kuryer topilmadi yoki uning hisobi faol emas. "
            "Kuryerlar ro'yxatini yangilang.",
            status.HTTP_404_NOT_FOUND,
        )

    courier = profile.user

    with transaction.atomic():
        order.courier = courier

        if order.status == "new":
            order.status = "confirmed"

        order.save(update_fields=["courier", "status"])

    return Response({
        "message": "Buyurtma kuryerga muvaffaqiyatli biriktirildi.",
        "order_id": order.id,
        "courier_id": courier.id,
        "courier_name": (
            courier.get_full_name() or courier.username
        ),
        "status": order.status,
    })






from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Order, UserProfile


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_courier_location(request, order_id):
    # Foydalanuvchi kuryer ekanini tekshirish
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Kuryer profili topilmadi."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if (
        profile.role != "courier"
        or not profile.is_active
        or not request.user.is_active
    ):
        return Response(
            {"error": "Faqat faol kuryer GPS yuborishi mumkin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Koordinatalarni tekshirish
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")

    try:
        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
    except (InvalidOperation, ValueError, TypeError):
        return Response(
            {"error": "Latitude va longitude son bo'lishi kerak."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not latitude.is_finite() or not longitude.is_finite():
        return Response(
            {"error": "Koordinatalar noto'g'ri."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not (-90 <= latitude <= 90):
        return Response(
            {"error": "Latitude -90 va 90 oralig'ida bo'lishi kerak."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not (-180 <= longitude <= 180):
        return Response(
            {"error": "Longitude -180 va 180 oralig'ida bo'lishi kerak."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Faqat shu kuryerga biriktirilgan buyurtma
    try:
        order = Order.objects.get(
            pk=order_id,
            courier=request.user,
        )
    except Order.DoesNotExist:
        return Response(
            {"error": "Buyurtma topilmadi yoki sizga biriktirilmagan."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if order.status in ["delivered", "cancelled"]:
        return Response(
            {"error": "Yakunlangan buyurtma uchun GPS yangilanmaydi."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.courier_latitude = latitude
    order.courier_longitude = longitude
    order.save(
        update_fields=[
            "courier_latitude",
            "courier_longitude",
        ]
    )

    return Response({
        "message": "Kuryer joylashuvi yangilandi.",
        "order_id": order.id,
        "latitude": float(order.courier_latitude),
        "longitude": float(order.courier_longitude),
    })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, InvalidOperation

from .models import Order


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_customer_location(request, order_id):
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")

    if latitude is None or longitude is None:
        return Response(
            {"error": "Latitude va longitude kerak."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
    except (InvalidOperation, ValueError, TypeError):
        return Response(
            {"error": "Koordinatalar noto'g'ri formatda."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return Response(
            {"error": "Koordinatalar diapazondan tashqarida."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return Response(
            {"error": "Buyurtma topilmadi."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Bu yerda buyurtma aynan joriy mijozga tegishliligi
    # tekshirilishi shart. Mijoz modeli/bog'lanishi aniqlangach,
    # shu tekshiruvni loyihangizga moslab qo'shamiz.

    order.customer_latitude = latitude
    order.customer_longitude = longitude
    order.save(
        update_fields=["customer_latitude", "customer_longitude"]
    )

    return Response({
        "message": "Mijoz koordinatalari saqlandi.",
        "order_id": order.id,
        "customer_latitude": order.customer_latitude,
        "customer_longitude": order.customer_longitude,
    })