from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from tracker.models import Order, OrderAttachment, Customer, Branch
import base64
import io

class AttachmentsSignatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.branch = Branch.objects.create(name='B1', code='B1')
        self.customer = Customer.objects.create(code='C1', full_name='John Doe', phone='123')
        self.order = Order.objects.create(order_number='O100', branch=self.branch, customer=self.customer, type='service')
        self.client.login(username='tester', password='pass')

    def test_add_multiple_attachments(self):
        url = reverse('tracker:add_order_attachments', kwargs={'pk': self.order.pk})
        f1 = SimpleUploadedFile('a.txt', b'hello', content_type='text/plain')
        f2 = SimpleUploadedFile('b.png', b'\x89PNG\r\n\x1a\n', content_type='image/png')
        resp = self.client.post(url, {'attachments': [f1, f2]})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(OrderAttachment.objects.filter(order=self.order).count(), 2)

    def test_reject_unsupported_attachment(self):
        url = reverse('tracker:add_order_attachments', kwargs={'pk': self.order.pk})
        f = SimpleUploadedFile('bad.exe', b'fakeexe', content_type='application/octet-stream')
        resp = self.client.post(url, {'attachments': [f]})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(OrderAttachment.objects.filter(order=self.order).count(), 0)

    def test_complete_order_with_base64_signature_and_attachment(self):
        url = reverse('tracker:complete_order', kwargs={'pk': self.order.pk})
        # create a tiny PNG base64 (1x1 transparent)
        png_base64 = (
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA' 
            'ASsJTYQAAAAASUVORK5CYII='
        )
        att = SimpleUploadedFile('doc.txt', b'contents', content_type='text/plain')
        resp = self.client.post(url, {'signature_data': png_base64, 'completion_attachment': att})
        self.assertEqual(resp.status_code, 302)
        o = Order.objects.get(pk=self.order.pk)
        self.assertEqual(o.status, 'completed')
        self.assertIsNotNone(o.signature_file)
        self.assertIsNotNone(o.completion_attachment)

    def test_reject_large_signature(self):
        url = reverse('tracker:complete_order', kwargs={'pk': self.order.pk})
        # create large fake base64 by repeating data
        large_data = 'data:image/png;base64,' + base64.b64encode(b'a'* (3 * 1024 * 1024)).decode()
        resp = self.client.post(url, {'signature_data': large_data})
        self.assertEqual(resp.status_code, 302)
        o = Order.objects.get(pk=self.order.pk)
        self.assertNotEqual(o.status, 'completed')
