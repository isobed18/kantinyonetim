from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsStaffOrAdmin
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from apps.stock.models import Stock
from apps.users.models import User
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
from apps.users.utils import log_user_action, notify_staff_new_order, notify_order_status_change, create_notification
from apps.menu.models import MenuItem
import whisper
import requests
from rest_framework.decorators import api_view, permission_classes
import json
import tempfile
import os
import time
import re
# Create your views here.

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()  # router icin default queryset
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', 'customer') in ['staff', 'admin']:
            return Order.objects.select_related('user').prefetch_related(
                'order_items__menu_item'
            ).all()
        if user.is_authenticated:
            return Order.objects.select_related('user').prefetch_related(
                'order_items__menu_item'
            ).filter(user=user)
        return Order.objects.none()

    def get_permissions(self):
        # authenticated userlarin kendi orderlarini create etme, okuma ve cancel etme islemlerine izin verme
        if self.action in ['list', 'retrieve', 'cancel', 'create_from_cart']:
            return [IsAuthenticated()]
        # diger islemler (update/delete) staff/admin ile kisitli
        return [IsStaffOrAdmin()]
   
    @action(detail=False, methods=['post'], url_path='create-from-cart')
    @transaction.atomic
    def create_from_cart(self, request):
        user = self.request.user
        cart_items = request.data.get('items', [])
        
        if not cart_items:
            return Response({'detail': 'Sepetiniz boş.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Stok kontrolü
        for item_data in cart_items:
            menu_item_id = item_data.get('menu_item')
            quantity = item_data.get('qty')
            try:
                stock = Stock.objects.select_for_update().get(menu_item_id=menu_item_id)
                if stock.quantity < quantity:
                    menu_item = MenuItem.objects.get(id=menu_item_id)
                    return Response(
                        {'detail': f'"{menu_item.name}" için stok yetersiz.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (Stock.DoesNotExist, MenuItem.DoesNotExist):
                return Response(
                    {'detail': f'ID {menu_item_id} olan ürün bulunamadı veya stok bilgisi yok.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Sipariş oluşturma
        order = Order.objects.create(user=user)
        for item_data in cart_items:
            menu_item = MenuItem.objects.get(id=item_data.get('menu_item'))
            quantity = item_data.get('qty')
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=quantity,
                price_at_order_time=menu_item.price
            )
            # Stoktan düşme
            stock = Stock.objects.get(menu_item=menu_item)
            stock.quantity -= quantity
            stock.save()

        order.update_total() # Sipariş toplamını güncelle

        # 3. Loglama ve bildirimler
        log_user_action(
            user=user,
            action='order_placed',
            resource_type='order',
            resource_id=order.id,
            details={'total': str(order.total), 'item_count': len(cart_items)},
            request=request
        )
        notify_staff_new_order(order, user)
        # Müşteriye bildirim create_notification ile notify_order_status_change içinde yapılıyor.
        
        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status
        new_status = request.data.get('status', old_status)

        # eger order zaten cancelled ise status degisikligini engelleme
        if old_status == 'cancelled' and new_status != 'cancelled':
            return Response({'detail': 'Cannot change status of a cancelled order.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # orderi update etme
        response = super().update(request, *args, **kwargs)
        
        # eger status cancelleddan non-cancelled bir statusa degistiyse is_restockedi resetleme
        if old_status == 'cancelled' and instance.status != 'cancelled':
            instance.is_restocked = False
            instance.save(update_fields=['is_restocked'])

        # status degisti mi kontrol etme
        if old_status != instance.status:
            print(f"Order status changed from {old_status} to {instance.status} for order {instance.id}")
            print(f"User performing update: {request.user.username} (ID: {request.user.id}, IsAuthenticated: {request.user.is_authenticated})")
            # status degisikligini loglama
            log_user_action(
                user=request.user,
                action='order_status_changed',
                resource_type='order',
                resource_id=instance.id,
                 details={
                    'old_status': old_status,
                    'new_status': instance.status,
                    'customer': instance.user.username
                 },
                 request=request
             )
            print(f"log_user_action for order status change called.")
            
            # bildirimleri gonderme
            notify_order_status_change(instance, old_status, instance.status, request.user, request)
        
        return response

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        order = self.get_object()

        # sadece order pending veya preparing ise restock etme
        if order.status in ['pending', 'preparing']:
            for item in order.order_items.select_related('menu_item').all():
                stock = Stock.objects.select_for_update().get(menu_item=item.menu_item)
                stock.quantity += item.quantity
                stock.save()
                log_user_action(
                    user=request.user,
                    action='item_cancelled',
                    resource_type='order_item',
                    resource_id=item.id,
                    details={'order_id': order.id, 'menu_item': item.menu_item.name, 'cancelled_quantity': item.quantity, 'full_cancellation': True, 'via_order_cancel': True},
                    request=request
                )
        
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        # musteriyi order cancel hakkinda bilgilendirme
        create_notification(
            recipient=order.user,
            notification_type='order_status',
            title='Order Cancelled',
            message=f'Your order #{order.id} has been cancelled.',
            priority='medium',
            resource_type='order',
            resource_id=order.id
        )
        return Response({'detail': 'Order cancelled.'}, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='reassign', permission_classes=[IsStaffOrAdmin])
    def reassign(self, request, pk=None):
        order = self.get_object()
        target_user_id = request.data.get('user')
        if not target_user_id:
            return Response({'user': 'Target user id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response({'user': 'Target user not found.'}, status=status.HTTP_404_NOT_FOUND)
        order.user = target_user
        order.save(update_fields=['user'])
        # Log reassign action
        log_user_action(
            user=request.user,
            action='reassign',
            resource_type='order',
            resource_id=order.id,
            details={'old_customer': order.user.username, 'new_customer': target_user.username},
            request=request
        )
        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_user_action(
            user=request.user,
            action='delete',
            resource_type='order',
            resource_id=instance.id,
            details={'order_id': instance.id, 'total': str(instance.total), 'customer': instance.user.username},
            request=request
        )
        return super().destroy(request, *args, **kwargs)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', 'customer') in ['staff', 'admin']:
            return OrderItem.objects.all().select_related('order__user', 'menu_item')
        if user.is_authenticated:
            return OrderItem.objects.filter(order__user=user).select_related('order__user', 'menu_item')
        return OrderItem.objects.none()

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsStaffOrAdmin()]

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        # kaydetmeden once eski degerleri yakalama
        old_price_at_order_time = serializer.instance.price_at_order_time
        old_quantity = serializer.instance.quantity
        
        # instancei kaydetme (bu, validated_data based instancei update edecek)
        updated_instance = serializer.save()

        # price degisikligi olduysa loglama
        if old_price_at_order_time != updated_instance.price_at_order_time:
            log_user_action(
                user=self.request.user,
                action='price_changed',
                resource_type='order_item',
                resource_id=updated_instance.id,
                details={
                    'order_id': updated_instance.order.id,
                    'menu_item': updated_instance.menu_item.name,
                    'old_price': str(old_price_at_order_time),
                    'new_price': str(updated_instance.price_at_order_time)
                },
                request=self.request
            )
        # quantity degisikligi olduysa loglama
        if old_quantity != updated_instance.quantity:
            log_user_action(
                user=self.request.user,
                action='update',
                resource_type='order_item',
                resource_id=updated_instance.id,
                details={
                    'order_id': updated_instance.order.id,
                    'menu_item': updated_instance.menu_item.name,
                    'old_quantity': old_quantity,
                    'new_quantity': updated_instance.quantity
                },
                request=self.request
            )

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        user = request.user

        print(f"OrderItem cancel attempt by user: {user.username} (ID: {user.id}), Role: {getattr(user, 'role', 'N/A')}")
        print(f"Order Item ID: {instance.id}, Associated Order User ID: {instance.order.user_id}, Owner ID: {instance.order.user.id}, Request User ID: {user.id}")
        
        # owner veya staff/admin line itemlari cancel edebilir
        if instance.order.user.id != user.id and not (getattr(user, 'role', 'customer') in ['staff', 'admin']):
            print("Permission denied for OrderItem cancel. User is not staff/admin and not order owner.")
            return Response({'detail': 'Not permitted to cancel this item.'}, status=status.HTTP_403_FORBIDDEN)
        print("Permission granted for OrderItem cancel.")

        # quantity ile partial cancellation destegi
        try:
            cancel_qty = int(request.data.get('quantity')) if 'quantity' in request.data else instance.quantity
        except Exception:
            return Response({'quantity': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)
        if cancel_qty <= 0:
            return Response({'quantity': 'Quantity must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)
        if cancel_qty > instance.quantity:
            return Response({'quantity': 'Cannot cancel more than existing quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        if instance.order.status in ['pending', 'preparing']:
            stock = Stock.objects.select_for_update().get(menu_item=instance.menu_item)
            stock.quantity += cancel_qty
            stock.save()

        old_quantity = instance.quantity # degisiklikten once eski quantity'yi yakalama

        if cancel_qty == instance.quantity:
            log_user_action(
                user=request.user,
                action='item_cancelled',
                resource_type='order_item',
                resource_id=instance.id,
                details={'order_id': instance.order.id, 'menu_item': instance.menu_item.name, 'cancelled_quantity': cancel_qty, 'full_cancellation': True},
                request=request
            )
            instance.delete()
        else:
            instance.quantity -= cancel_qty
            instance.save(update_fields=['quantity'])
            log_user_action(
                user=request.user,
                action='item_cancelled',
                resource_type='order_item',
                resource_id=instance.id,
                details={'order_id': instance.order.id, 'menu_item': instance.menu_item.name, 'cancelled_quantity': cancel_qty, 'new_quantity': instance.quantity, 'full_cancellation': False},
                request=request
            )
        
        # musteriyi item cancel hakkinda bilgilendirme
        create_notification(
            recipient=instance.order.user,
            notification_type='order_status',
            title='Order Item Cancelled',
            message=f'{cancel_qty}x {instance.menu_item.name} from your order #{instance.order.id} has been cancelled.',
            priority='medium',
            resource_type='order_item',
            resource_id=instance.id
        )
        
        msg = 'Order item cancelled and restocked.' if instance.order.status in ['pending', 'preparing'] else 'Order item cancelled (no restock due to order status).'
        return Response({'detail': msg}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        # staff/admin veya orderin sahibi ise izin verme
        if not (getattr(user, 'role', 'customer') in ['staff', 'admin'] or instance.order.user_id == user.id):
            return Response({'detail': 'Not permitted to delete this item.'}, status=status.HTTP_403_FORBIDDEN)
        order = instance.order
        # sadece order henuz ready/completed/cancelled degilse restock etme
        if order.status in ['pending', 'preparing']:
            stock = Stock.objects.select_for_update().get(menu_item=instance.menu_item)
            stock.quantity += instance.quantity
            stock.save()
        log_user_action(
            user=request.user,
            action='delete',
            resource_type='order_item',
            resource_id=instance.id,
            details={'order_id': instance.order.id, 'menu_item': instance.menu_item.name, 'quantity': instance.quantity},
            request=request
        )
        return super().destroy(request, *args, **kwargs)
    


whisper_model = None

def load_whisper():
    global whisper_model
    if whisper_model is None:
        print("whisper yükleniyor")
        whisper_model = whisper.load_model("base", device = "cuda" )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_voice_order(request):
    start_time_whisper = time.time()
    load_whisper()
    audio_file = request.FILES.get('audio')

    if not audio_file:
        return Response({"detail" : "Ses dosyası bulanamadı."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # geçici dosyaya yazma        
        temp_dir = tempfile.mkdtemp()
        tmp_file_path = os.path.join(temp_dir, 'voice_order.mp3')
        
        with open(tmp_file_path, 'wb') as tmp_file:
            tmp_file.write(audio_file.read())

        # whisper transkripsyon 
        result = whisper_model.transcribe(tmp_file_path, language="tr")
        transcribed_text = result["text"]
        print(f"Whisper Çıktısı: {transcribed_text}")
    
    except Exception as e:
        return Response({"detail": f"ses dönüştürme hatası: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # dosyayı temizleme
        whisper_duration = time.time() - start_time_whisper
        print(f"whisper çalışma süresi:{whisper_duration}")
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            os.rmdir(temp_dir)

    # menu
    menu_items = list(MenuItem.objects.all().values_list('name', flat=True))
    
    prompt = f"""
    Sen bir kantin sipariş asistanısın. Kullanıcının siparişini JSON formatında çıkar. Sadece JSON döndür, başka bir şey yazma.
    Mevcut ürünler: adana, çay, ayran, tavuk döner, T-bone, patates kızartması, fırın sütlaç, tost. Yazıyla yazılmış sayıları, sayıya dönüştür.
    example: 10 thousand == 10000
    JSON format example: {{"orders": [{{"item": "Çay", "quantity": 2}}, {{"item": "Tost", "quantity": 1}}]}}.

    User's text: "25 çay, pardon 28 oldu, abi sen ne alırsın, abime bir tost, yanına ne alırsın, yanına ayran alayım"

    JSON:
    """
    ollama_api_url = "http://localhost:11434/api/generate"
    start_time_llama = time.time()
    print(prompt)
    try:
        ollama_response = requests.post(
            ollama_api_url,
            json={
                "model" : "llama-3p1-8b",
                "prompt" : prompt,
                "stream" : False,
                
            }
        )
        llama_duration = time.time() - start_time_llama
        print(f"llama duration: {llama_duration}")
        ollama_response.raise_for_status()

        llm_output = json.loads(ollama_response.text)
        order_details = json.loads(llm_output['response']).get('orders', [])
        print(f"llama çıktısı{llm_output}")
    except Exception as e:
        return Response({"detail": f"Ollama hata verdi: {e}"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not order_details:
        return Response({"detail": "sipariş içeriği boş lütfen terkar deneyiniz."})
    
    try: 
        with transaction.atomic():
            order_serializer = OrderSerializer(data={'user' : request.user.id}, context={'request': request})
            order_serializer.is_valid(raise_exception=True)
            order = order_serializer.save(user=request.user)
            
            order = order_serializer.save()
            for item_data in order_details:
                item_name = item_data.get('item')
                quantity =  item_data.get('quantity')
                if not item_name or not quantity:
                    continue
                menu_item = MenuItem.objects.get(name__iexact = item_name)
                order_item_data = {
                    "order" : order.id,
                    "menu_item" : menu_item.id,
                    "quantity" : quantity
                }
                order_item_serializer = OrderItemSerializer(data=order_item_data, context={'request': request})
                order_item_serializer.is_valid(raise_exception=True)
                order_item_serializer.save()
        return Response( {"message": "sesli sipariş alındı", "order_id" : order.id, "transcribed_text": transcribed_text}, status = status.HTTP_201_CREATED)
    except Exception as e:
        return Response( {"detail": f"siparişte beklenmedik hata oluştu: {e}"})