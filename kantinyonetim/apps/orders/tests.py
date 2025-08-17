from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.users.models import User
from apps.menu.models import MenuItem
from apps.stock.models import Stock
from apps.orders.models import Order, OrderItem


class OrderFlowTests(APITestCase):
    def setUp(self):
        # Users
        self.admin = User.objects.create(username='admin', role='admin', is_staff=True, is_superuser=True)
        self.admin.set_password('adminpass')
        self.admin.save()

        self.staff = User.objects.create(username='staff', role='staff', is_staff=True)
        self.staff.set_password('staffpass')
        self.staff.save()

        self.customer = User.objects.create(username='cust', role='customer')
        self.customer.set_password('custpass')
        self.customer.save()

        self.other_customer = User.objects.create(username='cust2', role='customer')
        self.other_customer.set_password('cust2pass')
        self.other_customer.save()

        # Menu and stock
        self.burger = MenuItem.objects.create(name='Burger', description='Beef burger', price=Decimal('10.00'), is_available=True)
        self.stock_burger = Stock.objects.create(menu_item=self.burger, quantity=10)

    def auth(self, username, password):
        res = self.client.post('/api/token/', {'username': username, 'password': password}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        token = res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_customer_creates_order_and_items_and_cannot_touch_others(self):
        # Customer creates order
        self.auth('cust', 'custpass')
        res = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id = res.data['id']

        # Add 3 burgers
        res = self.client.post('/api/order-items/', {
            'order': order_id,
            'menu_item': self.burger.id,
            'quantity': 3
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Stock decreased
        self.stock_burger.refresh_from_db()
        self.assertEqual(self.stock_burger.quantity, 7)

        # Other customer's order
        self.client.credentials()  # clear
        self.auth('cust2', 'cust2pass')
        res = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        other_order_id = res.data['id']

        # Customer cannot add to someone else's order
        res = self.client.post('/api/order-items/', {
            'order': order_id,  # belongs to cust
            'menu_item': self.burger.id,
            'quantity': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Owner can still add to own order
        self.client.credentials()
        self.auth('cust', 'custpass')
        res = self.client.post('/api/order-items/', {
            'order': order_id,
            'menu_item': self.burger.id,
            'quantity': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_price_override_and_staff_complete(self):
        # Admin creates order and overrides price
        self.auth('admin', 'adminpass')
        res = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id = res.data['id']

        res = self.client.post('/api/order-items/', {
            'order': order_id,
            'menu_item': self.burger.id,
            'quantity': 2,
            'price_at_order_time': '5.50'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item_id = res.data['id']

        # Staff marks order completed
        self.client.credentials()
        self.auth('staff', 'staffpass')
        res = self.client.patch(f'/api/orders/{order_id}/', {'status': 'completed'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_cancel_restock_and_delete_item_restock_rules(self):
        # Customer creates order and adds 2 burgers
        self.auth('cust', 'custpass')
        res = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id = res.data['id']
        res = self.client.post('/api/order-items/', {
            'order': order_id,
            'menu_item': self.burger.id,
            'quantity': 2
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item_id = res.data['id']

        # Cancel order (pending) → restock
        res = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.stock_burger.refresh_from_db()
        self.assertEqual(self.stock_burger.quantity, 10)

        # New order: pending, add 1, then delete item → restock
        res = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id2 = res.data['id']
        res = self.client.post('/api/order-items/', {
            'order': order_id2,
            'menu_item': self.burger.id,
            'quantity': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item_id2 = res.data['id']
        self.stock_burger.refresh_from_db()
        self.assertEqual(self.stock_burger.quantity, 9)
        # delete → restock to 10
        res = self.client.delete(f'/api/order-items/{item_id2}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.stock_burger.refresh_from_db()
        self.assertEqual(self.stock_burger.quantity, 10)

        # New order: add 1, then mark completed, then delete item → no restock
        res = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id3 = res.data['id']
        res = self.client.post('/api/order-items/', {
            'order': order_id3,
            'menu_item': self.burger.id,
            'quantity': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item_id3 = res.data['id']
        self.client.credentials()
        self.auth('staff', 'staffpass')
        res = self.client.patch(f'/api/orders/{order_id3}/', {'status': 'completed'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.credentials()
        self.auth('cust', 'custpass')
        res = self.client.delete(f'/api/order-items/{item_id3}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        # stock should remain 9
        self.stock_burger.refresh_from_db()
        self.assertEqual(self.stock_burger.quantity, 9)
