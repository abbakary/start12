from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import uuid


class Branch(models.Model):
    """Business branch/location for multi-region scoping."""
    name = models.CharField(max_length=128, unique=True)
    code = models.CharField(max_length=32, unique=True)
    region = models.CharField(max_length=128, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"], name="idx_branch_code"),
            models.Index(fields=["region"], name="idx_branch_region"),
        ]

    def __str__(self) -> str:
        r = f" ({self.region})" if self.region else ""
        return f"{self.name}{r}"


class Customer(models.Model):
    TYPE_CHOICES = [
        ("government", "Government"),
        ("ngo", "NGO"),
        ("company", "Private Company"),
        ("personal", "Personal"),
    ]
    PERSONAL_SUBTYPE = [("owner", "Owner"), ("driver", "Driver")]
    STATUS_CHOICES = [
        ("arrived", "Arrived"),
        ("in_service", "In Service"),
        ("completed", "Completed"),
        ("departed", "Departed"),
    ]

    code = models.CharField(max_length=32, unique=True, editable=False)
    branch = models.ForeignKey('Branch', on_delete=models.PROTECT, null=True, blank=True, related_name='customers')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True, null=True, help_text="WhatsApp number (if different from phone)")
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # keep this as "notes" so your forms work, but mark as deprecated
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='General notes about the customer (deprecated, use CustomerNote model instead)'
    )

    customer_type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    tax_number = models.CharField(max_length=64, blank=True, null=True)
    personal_subtype = models.CharField(max_length=16, choices=PERSONAL_SUBTYPE, blank=True, null=True)

    registration_date = models.DateTimeField(default=timezone.now)
    arrival_time = models.DateTimeField(blank=True, null=True)
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="arrived")

    total_visits = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_visit = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"CUST{str(uuid.uuid4())[:8].upper()}"
            while Customer.objects.filter(code=self.code).exists():
                self.code = f"CUST{str(uuid.uuid4())[:8].upper()}"
        if not self.arrival_time:
            self.arrival_time = timezone.now()
        super().save(*args, **kwargs)

    def get_icon_for_customer_type(self):
        """Return appropriate icon class based on customer type"""
        if not self.customer_type:
            return 'user'
        
        icon_map = {
            'government': 'landmark',
            'ngo': 'hands-helping',
            'company': 'building',
            'personal': 'user',
        }
        return icon_map.get(self.customer_type, 'user')
        
    def __str__(self):
        return f"{self.full_name} ({self.code})"

    class Meta:
        indexes = [
            models.Index(fields=["full_name"], name="idx_cust_name"),
            models.Index(fields=["phone"], name="idx_cust_phone"),
            models.Index(fields=["email"], name="idx_cust_email"),
            models.Index(fields=["registration_date"], name="idx_cust_reg"),
            models.Index(fields=["last_visit"], name="idx_cust_lastvisit"),
            models.Index(fields=["customer_type"], name="idx_cust_type"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "full_name", "phone", "organization_name", "tax_number"],
                name="uniq_customer_identity",
            )
        ]


class Vehicle(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=32)
    make = models.CharField(max_length=64, blank=True, null=True)
    model = models.CharField(max_length=64, blank=True, null=True)
    vehicle_type = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.plate_number} - {self.make or ''} {self.model or ''}"

    class Meta:
        indexes = [
            models.Index(fields=["customer"], name="idx_vehicle_customer"),
            models.Index(fields=["plate_number"], name="idx_vehicle_plate"),
        ]


class Order(models.Model):
    TYPE_CHOICES = [("service", "Service"), ("sales", "Sales"), ("inquiry", "Inquiries")]
    STATUS_CHOICES = [
        ("created", "New"),
        ("in_progress", "In Progress"),
        ("overdue", "Overdue"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PRIORITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    branch = models.ForeignKey('Branch', on_delete=models.PROTECT, null=True, blank=True, related_name='orders')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="created")
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="medium")

    description = models.TextField(blank=True, null=True)
    estimated_duration = models.PositiveIntegerField(blank=True, null=True, help_text="Minutes")
    actual_duration = models.PositiveIntegerField(blank=True, null=True)

    # Sales fields
    item_name = models.CharField(max_length=64, blank=True, null=True)
    brand = models.CharField(max_length=64, blank=True, null=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    tire_type = models.CharField(max_length=32, blank=True, null=True)

    # Consultation fields
    inquiry_type = models.CharField(max_length=64, blank=True, null=True)
    questions = models.TextField(blank=True, null=True)
    contact_preference = models.CharField(max_length=16, blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)

    # Timestamps and assignment
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_orders")

    # Completion evidence and signer
    signature_file = models.ImageField(upload_to='order_signatures/', blank=True, null=True)
    completion_attachment = models.FileField(upload_to='order_attachments/', blank=True, null=True)
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_signed')
    signed_at = models.DateTimeField(blank=True, null=True)
    # completion_date is kept for historical compatibility; completed_at is canonical timestamp used across views

    # Additional fields used across the app
    completion_date = models.DateTimeField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)

    # Job card/identification number for quick order lookup (optional)
    job_card_number = models.CharField(max_length=64, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.order_number} - {self.customer.full_name}"

    def auto_progress_if_elapsed(self):
        """Automatically move created -> in_progress after 10 minutes."""
        if self.status == 'created' and (timezone.now() - self.created_at) >= timedelta(minutes=10):
            self.status = 'in_progress'
            self.started_at = self.started_at or timezone.now()
            self.save(update_fields=['status', 'started_at'])

    class Meta:
        indexes = [
            models.Index(fields=["order_number"], name="idx_order_number"),
            models.Index(fields=["status"], name="idx_order_status"),
            models.Index(fields=["type"], name="idx_order_type"),
            models.Index(fields=["created_at"], name="idx_order_created"),
        ]

    def _generate_order_number(self) -> str:
        """Generate a unique human-friendly order number."""
        from uuid import uuid4

        prefix = 'ORD'
        base = timezone.now().strftime('%Y%m%d%H%M%S')
        # Retry until unique to avoid collision under concurrent requests
        for _ in range(5):
            candidate = f"{prefix}{base}{uuid4().hex[:4].upper()}"
            if not Order.objects.filter(order_number=candidate).exists():
                return candidate
        # Fallback to full UUID if repeated collisions occur
        return f"{prefix}{uuid4().hex.upper()}"

    def save(self, *args, **kwargs):
        """Ensure order numbers exist and inquiries auto-complete."""
        if not self.order_number:
            self.order_number = self._generate_order_number()
        # If this is an inquiry, make it completed and set completed timestamps
        if self.type == 'inquiry':
            now = timezone.now()
            # Preserve any explicit completed_at if already provided, otherwise set
            if not self.completed_at:
                self.completed_at = now
            if not self.completion_date:
                self.completion_date = now
            # Force status to completed
            self.status = 'completed'
        super().save(*args, **kwargs)


class OrderAttachment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='order_attachments/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_order_attachments')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    def filename(self):
        try:
            return self.file.name.split('/')[-1]
        except Exception:
            return self.file.name

    def __str__(self):
        return f"Attachment #{self.id} for {self.order.order_number}"

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['order'], name='idx_order_attachment_order'),
            models.Index(fields=['uploaded_at'], name='idx_order_att_uploaded_at'),
        ]


class Brand(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_brand_name"),
            models.Index(fields=["is_active"], name="idx_brand_active"),
        ]

    def __str__(self) -> str:
        return self.name


class InventoryItem(models.Model):
    name = models.CharField(max_length=128)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sku = models.CharField(max_length=64, blank=True, null=True)
    barcode = models.CharField(max_length=64, blank=True, null=True)
    reorder_level = models.PositiveIntegerField(default=5)
    location = models.CharField(max_length=128, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_inv_name"),
            models.Index(fields=["quantity"], name="idx_inv_qty"),
            models.Index(fields=["is_active"], name="idx_inv_active"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["name", "brand"], name="uniq_item_brand_name")
        ]

    def __str__(self) -> str:
        b = self.brand.name if self.brand else "Unbranded"
        return f"{b} - {self.name}"


class InventoryAdjustment(models.Model):
    ADJUSTMENT_TYPES = (
        ("addition", "Addition"),
        ("removal", "Removal"),
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=16, choices=ADJUSTMENT_TYPES)
    quantity = models.PositiveIntegerField()
    reference = models.CharField(max_length=64, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    adjusted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_adjustments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at'], name='idx_inv_adj_created'),
            models.Index(fields=['adjustment_type'], name='idx_inv_adj_type'),
        ]

    # Backwards-friendly aliases used by older utility scripts
    @property
    def user(self):
        return self.adjusted_by

    @property
    def date(self):
        return self.created_at

    def __str__(self) -> str:
        return f"{self.get_adjustment_type_display()} {self.quantity} × {self.item}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Profile of {self.user.username}"


class CustomerNote(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='note_entries',
        related_query_name='note_entry',
    )
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer'], name='idx_cnote_customer'),
            models.Index(fields=['created_at'], name='idx_cnote_created'),
        ]

    def __str__(self) -> str:
        return f"Note for {self.customer.full_name} at {timezone.localtime(self.created_at).strftime('%Y-%m-%d %H:%M')}"


class ServiceType(models.Model):
    """Admin-managed service types for 'Service' orders with expected durations."""
    name = models.CharField(max_length=128, unique=True)
    estimated_minutes = models.PositiveIntegerField(default=30, help_text="Expected time in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_service_type_name"),
            models.Index(fields=["is_active"], name="idx_service_type_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.estimated_minutes}m)"


class ServiceAddon(models.Model):
    """Admin-managed add-on services for 'Sales' orders (e.g., installation, balancing)."""
    name = models.CharField(max_length=128, unique=True)
    estimated_minutes = models.PositiveIntegerField(default=10, help_text="Expected time in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_service_addon_name"),
            models.Index(fields=["is_active"], name="idx_service_addon_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.estimated_minutes}m)"
