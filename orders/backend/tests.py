import os
import collections
from copy import deepcopy
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError
from django.db.utils import Error as DBError, ConnectionDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import ProductInfo, Order
from accounts.models import User, Contact


class APITests(APITestCase):
    first_buyer_data = {
        'first_name': 'User1',
        'last_name': 'User1',
        'email': 'User1@mail.com',
        'company': 'User1Company',
        'position': 'User1Position',
        'password': 'User1Password',
        'type': 'buyer',
        'contacts': [
            {'phone': '+79999999999',
             'city': 'User1City',
             'street': 'User1Street',
             'house': '1'},
            {'phone': '+79888888888'}
        ]
    }

    second_buyer_data = {
        'first_name': 'User2FirstName',
        'last_name': 'User2LastName',
        'email': 'User2@mail.com',
        'company': 'User2Company',
        'position': 'User2Position',
        'password': 'User2Password',
        'type': 'buyer',
        'contacts': []
    }


    def create_user(self, data):
        data = deepcopy(data)
        contact_data = data.pop('contacts', [])
        password = data.pop('password')
        user = User.objects.create(**data)
        user.is_active = True
        user.set_password(password)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact)
            except (DBError, ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError, ConnectionDoesNotExist):
                break

        user.save()

    def login_user(self, email=None):
        if isinstance(email, collections.Mapping):
            email = email.get('email')
        if not email:
            self.clear_credentials()
            return
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def clear_credentials(self):
        self.client.credentials(HTTP_AUTHORIZATION='')

    def load_shop_data(self):
        with open(os.path.join(settings.MEDIA_ROOT, 'fixtures/shop1.yaml', 'rb')) as file:
            response = self.client.post(reverse('backend:partner-update'),
                                        data=encode_multipart(BOUNDARY, {'file': file}),
                                        content_type=MULTIPART_CONTENT)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_shop_state(self):
        self.login_user(self.first_shop_data)
        response = self.client.get(reverse('backend:partner-state'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('data', response.data)
        for item in response.data['data']:
            self.assertIn('url', item)
            self.assertIn('id', item)
            self.assertIn('name', item)
            self.assertIn('state', item)
        self.assertEqual(len(response.data['data']), 1)

    def test_set_shop_state(self):
        self.login_user(self.first_shop_data)

        response = self.client.post(reverse('backend:partner-state'), data={'state': 'True'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('state', response.data)
        self.assertTrue(response.data['state'])
        shops = User.objects.get(email=self.first_shop_data['email']).shops.all()
        for shop in shops:
            self.assertTrue(shop.state)

        response = self.client.post(reverse('backend:partner-state'), data={'state': 'False'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('state', response.data)
        self.assertFalse(response.data['state'])
        shops = User.objects.get(email=self.first_shop_data['email']).shops.all()
        for shop in shops:
            self.assertFalse(shop.state)

    def test_get_contacts_shop_user(self):
        self.login_user(self.first_shop_data)
        response = self.client.get(reverse('backend:user-contact'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('results', response.data)
        for item in response.data['results']:
            self.assertIn('phone', item)
            self.assertIn('city', item)
            self.assertIn('street', item)
            self.assertIn('house', item)
            self.assertIn('structure', item)
            self.assertIn('apartment', item)
        self.assertEqual(len(response.data['results']), len(self.first_shop_data['contacts']))

    def test_get_contacts_buyer(self):
        self.login_user(self.first_buyer_data)
        response = self.client.get(reverse('backend:user-contact'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('results', response.data)
        for item in response.data['results']:
            self.assertIn('phone', item)
            self.assertIn('city', item)
            self.assertIn('street', item)
            self.assertIn('house', item)
            self.assertIn('structure', item)
            self.assertIn('apartment', item)
        self.assertEqual(len(response.data['results']), len(self.first_shop_data['contacts']))

    def test_delete_contact_buyer(self):
        self.login_user(self.first_buyer_data)
        contacts = User.objects.get(email=self.first_buyer_data['email']).contacts
        old_count = contacts.count()
        id = contacts.first().id
        response = self.client.delete(reverse('backend:contact-detail', kwargs={'pk': id}), format='json')
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(count + 1, old_count)

    def test_get_product_info(self, query=''):
        response = self.client.get(reverse('backend:products') + query, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('results', response.data)
        for item in response.data['results']:
            self.assertIn('id', item)
            self.assertIn('product', item)
            self.assertIn('shop', item)
            self.assertIn('quantity', item)
            self.assertIn('price', item)
            self.assertIn('price_rrc', item)
            self.assertIn('product_parameters', item)

            product = item['product']
            self.assertIn('name', product)
            self.assertIn('category', product)

            category = product['category']
            self.assertIn('id', category)
            self.assertIn('name', category)

            shop = item['shop']
            self.assertIn('name', shop)

            for entry in item['product_parameters']:
                self.assertIn('parameter', entry)
                self.assertIn('value', entry)

    def test_add_item_to_basket(self):
        self.login_user(self.first_buyer_data)
        user = User.objects.get(email=self.first_buyer_data['email'])
        id = ProductInfo.objects.first().id
        quantity = 5
        response = self.client.put(reverse('backend:basket'), format='json',
                                   data={'product_info': id, 'quantity': quantity})

        self.assertTrue(Order.objects.filter(user_id=user.id, state='basket').exists())
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(ordered_items.count(), 1)
        self.assertEqual(ordered_items.first().product_info_id, id)
        self.assertEqual(ordered_items.first().quantity, quantity)

    def test_make_order(self):
        self.test_add_item_to_basket()
        user = User.objects.get(email=self.first_buyer_data['email'])
        contact = user.contacts.first()

        response = self.client.post(reverse('backend:order'), format='json',
                                    data={'contact': contact.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertTrue(user.orders.filter(state='new').exists())
