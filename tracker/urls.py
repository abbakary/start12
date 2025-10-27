from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.contrib.auth.views import LogoutView
from . import views
from .views import CustomLoginView, CustomLogoutView
from .views_api_fix import api_customer_groups_data_fixed
from . import branch_metrics as views_branch
from . import views_documents
from . import views_quick_start

app_name = "tracker"

urlpatterns = [
    # Authentication
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    
    # Main app
    path("", views.dashboard, name="dashboard"),
    path("customers/", views.customers_list, name="customers_list"),
    path("customers/search/", views.customers_search, name="customers_search"),
    path("customers/quick-create/", views.customers_quick_create, name="customers_quick_create"),
    path("customers/register/", views.customer_register, name="customer_register"),
    path("customers/export/", views.customers_export, name="customers_export"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/request-access/", views.request_customer_access, name="request_customer_access"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/<int:pk>/delete/", views.customer_delete, name="customer_delete"),
    path("customers/<int:pk>/note/", views.add_customer_note, name="add_customer_note"),
    path("customers/<int:customer_id>/note/<int:note_id>/delete/", views.delete_customer_note, name="delete_customer_note"),
    path("customers/<int:pk>/order/new/", views.create_order_for_customer, name="create_order_for_customer"),
    path("customer-groups/", views.customer_groups_advanced, name="customer_groups"),
    path("customer-groups/advanced/", views.customer_groups_advanced, name="customer_groups_advanced"),
    path("api/customer-groups-data/", views.api_customer_groups_data, name="api_customer_groups_data"),
    path("api/customer-groups-data-fixed/", api_customer_groups_data_fixed, name="api_customer_groups_data_fixed"),
    path("customer-groups/export/", views.customer_groups_export, name="customer_groups_export"),
    path("api/customer-groups/data/", views.customer_groups_data, name="customer_groups_data"),
    path("api/customers/summary/", views.api_customers_summary, name="api_customers_summary"),

    path("orders/", views.orders_list, name="orders_list"),
    path("orders/export/", views.orders_export, name="orders_export"),
    path("orders/new/", views.start_order, name="order_start"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/edit/", views.order_edit, name="order_edit"),
    path("orders/<int:pk>/delete/", views.order_delete, name="order_delete"),
    path("orders/<int:pk>/status/", views.update_order_status, name="update_order_status"),
    path("orders/<int:pk>/complete/", views.complete_order, name="complete_order"),
    path("orders/<int:pk>/attachments/add/", views.add_order_attachments, name="add_order_attachments"),
    path("orders/<int:pk>/sign-document/", views.sign_order_document, name="order_sign_document"),
    path("orders/<int:pk>/sign-existing-document/", views.sign_existing_document, name="sign_existing_document"),
    path("attachments/<int:att_id>/delete/", views.delete_order_attachment, name="delete_order_attachment"),
    path("api/orders/<int:pk>/status/", views.api_order_status, name="api_order_status"),
    path("api/orders/statuses/", views.api_orders_statuses, name="api_orders_statuses"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),

    path("analytics/", views.analytics, name="analytics"),
    path("analytics/customer/", views.analytics_customer, name="analytics_customer"),
    path("analytics/service/", views.analytics_service, name="analytics_service"),
    path("analytics/performance/", views.analytics_performance, name="analytics_performance"),
    path("analytics/revenue/", views.analytics_revenue, name="analytics_revenue"),
   

    # Reports
    path("reports/", views.reports, name="reports"),
    path("reports/advanced/", views.reports_advanced, name="reports_advanced"),
    path("reports/export/", views.reports_export, name="reports_export"),
    path("reports/export/pdf/", views.reports_export_pdf, name="reports_export_pdf"),

    # Inquiry management
    path("inquiries/", views.inquiries, name="inquiries"),
    path("inquiries/<int:pk>/", views.inquiry_detail, name="inquiry_detail"),
    path("inquiries/<int:pk>/respond/", views.inquiry_respond, name="inquiry_respond"),
    path("inquiries/<int:pk>/status/", views.update_inquiry_status, name="update_inquiry_status"),

    # Inventory (manager/admin)
    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/new/", views.inventory_create, name="inventory_create"),
    path("inventory/<int:pk>/edit/", views.inventory_edit, name="inventory_edit"),
    path("inventory/<int:pk>/delete/", views.inventory_delete, name="inventory_delete"),
    path("inventory/stock-management/", views.inventory_stock_management, name="inventory_stock_management"),
    path("inventory/low-stock/", views.inventory_low_stock, name="inventory_low_stock"),

    # Service settings
    path("services/types/", views.service_types_list, name="service_types_list"),
    path("services/addons/", views.service_addons_list, name="service_addons_list"),
    path("api/services/types/create/", views.create_service_type, name="create_service_type"),
    path("api/services/types/<int:pk>/update/", views.update_service_type, name="update_service_type"),
    path("api/services/addons/create/", views.create_service_addon, name="create_service_addon"),
    path("api/services/addons/<int:pk>/update/", views.update_service_addon, name="update_service_addon"),

    # Brand management
    path("brands/", views.brand_list, name="brand_list"),


    # Admin-only Organization Management
    path("organization/", views.organization_management, name="organization"),
    path("organization/export/", views.organization_export, name="organization_export"),

    # Vehicle management
    path("vehicles/<int:customer_id>/add/", views.vehicle_add, name="vehicle_add"),
    path("vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("api/customers/<int:customer_id>/vehicles/", views.api_customer_vehicles, name="api_customer_vehicles"),

    # User management (admin)
    path("users/", views.users_list, name="users_list"),
    path("users/add/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/toggle/", views.user_toggle_active, name="user_toggle_active"),
    path("users/<int:pk>/reset/", views.user_reset_password, name="user_reset_password"),

    # Internal admin console: system settings and tools
    path("console/settings/", views.system_settings, name="system_settings"),
    path("console/audit-logs/", views.audit_logs, name="audit_logs"),
    path("console/backup/", views.backup_restore, name="backup_restore"),

    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),

    path("api/orders/recent/", views.api_recent_orders, name="api_recent_orders"),
    path("api/branch-metrics/", views_branch.api_branch_metrics, name="api_branch_metrics"),
    path("api/inventory/items/", views.api_inventory_items, name="api_inventory_items"),
    path("api/inventory/brands/", views.api_inventory_brands, name="api_inventory_brands"),
    path("api/inventory/stock/", views.api_inventory_stock, name="api_inventory_stock"),
    path("api/inventory/create-item/", views.api_create_item_with_brand, name="api_create_item_with_brand"),
    path("api/brands/create/", views.create_brand, name="api_create_brand"),
    path("api/brands/<int:pk>/update/", views.update_brand, name="api_update_brand"),
    path("api/customers/<int:customer_id>/vehicles/", views.api_customer_vehicles, name="api_customer_vehicles"),
    # Notifications summary (canonical)
    path("api/notifications/summary/", views.api_notifications_summary, name="api_notifications_summary"),
    # Aliases to tolerate typos/missing trailing slash
    path("api/notifications/summary", views.api_notifications_summary),
    path("api/notification/summary/", views.api_notifications_summary, name="api_notifications_summary_singular"),
    path("api/notification/summary", views.api_notifications_summary),
    path("api/customers/check-duplicate/", views.api_check_customer_duplicate, name="api_check_customer_duplicate"),
    path("api/service-distribution/", views.api_service_distribution, name="api_service_distribution"),

    # Document upload and extraction
    path("api/documents/upload/", views_documents.upload_document, name="api_upload_document"),
    path("api/documents/<int:doc_id>/extraction/", views_documents.get_document_extraction, name="api_get_document_extraction"),
    path("api/documents/create-order/", views_documents.create_order_from_document, name="api_create_order_from_document"),
    path("api/documents/verify-extraction/", views_documents.verify_and_update_extraction, name="api_verify_extraction"),
    path("api/documents/search-job-card/", views_documents.search_by_job_card, name="api_search_job_card"),
    path("api/orders/quick-start/", views_documents.start_quick_order, name="api_quick_start_order"),

    # Quick Start Integration
    path("customer/register-with-extraction/", views_quick_start.customer_register_with_extraction, name="customer_register_extraction"),
    path("customer/register-with-extraction/<str:vehicle_plate>/", views_quick_start.customer_register_with_extraction, name="customer_register_extraction_plate"),
    path("orders/create-with-extraction/", views_quick_start.order_create_with_extraction, name="order_create_extraction"),
    path("api/quick-start/auto-fill-order/", views_quick_start.auto_fill_order_from_extraction, name="api_auto_fill_order"),
    path("api/quick-start/detect-customer-mismatch/", views_quick_start.detect_and_merge_customer_data, name="api_detect_mismatch"),
    path("api/quick-start/apply-customer-merge/", views_quick_start.apply_customer_data_merge, name="api_apply_merge"),
]
