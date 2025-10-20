def add_inventory_stock_management_view():
    import re
    from pathlib import Path
    
    # Path to the views.py file
    views_path = Path('c:/Users/abbak/Posdoll/tracker/views.py')
    
    # Read the current content
    content = views_path.read_text(encoding='utf-8')
    
    # Check if the function already exists
    if 'def inventory_stock_management' in content:
        print("inventory_stock_management view already exists")
        return
    
    # The new function to add
    new_function = """
@login_required
@is_manager
def inventory_stock_management(request: HttpRequest):
    \"\"\"View for managing inventory stock levels and adjustments\"\"\"
    from .models import InventoryItem, InventoryAdjustment
    from .forms import InventoryAdjustmentForm
    from django.db.models import Sum, F, ExpressionWrapper, FloatField
    from django.db.models.functions import Coalesce
    from django.shortcuts import render, redirect
    from django.contrib import messages
    
    # Get all active inventory items with current stock levels
    items = InventoryItem.objects.filter(is_active=True).order_by('name')
    
    # Calculate total value for each item
    items = items.annotate(
        total_value=ExpressionWrapper(
            F('price') * F('quantity'),
            output_field=FloatField()
        )
    )
    
    # Handle stock adjustment form submission
    if request.method == 'POST':
        form = InventoryAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment = form.save(commit=False)
            adjustment.user = request.user
            adjustment.save()
            
            # Update the inventory item quantity
            item = adjustment.item
            if adjustment.adjustment_type == 'add':
                item.quantity += adjustment.quantity
            else:
                item.quantity = max(0, item.quantity - adjustment.quantity)  # Prevent negative quantities
            item.save()
            
            messages.success(request, f'Stock level updated for {item.name}')
            return redirect('tracker:inventory_stock_management')
    else:
        form = InventoryAdjustmentForm()
    
    # Get recent adjustments
    recent_adjustments = InventoryAdjustment.objects.select_related('item', 'user').order_by('-date')[:10]
    
    # Calculate inventory summary
    summary = {
        'total_items': items.count(),
        'total_quantity': items.aggregate(total=Sum('quantity'))['total'] or 0,
        'total_value': items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0,
        'low_stock_count': items.filter(quantity__lte=F('reorder_level')).count(),
    }
    
    return render(request, 'tracker/inventory_stock_management.html', {
        'items': items,
        'form': form,
        'recent_adjustments': recent_adjustments,
        'summary': summary,
    })
"""
    
    # Find the inventory_list function and insert our new function before it
    if 'def inventory_list' in content:
        # Insert the new function before inventory_list
        modified_content = content.replace(
            '@login_required\n@is_manager\ndef inventory_list', 
            new_function + '\n\n@login_required\n@is_manager\ndef inventory_list'
        )
        
        # Write the modified content back to the file
        views_path.write_text(modified_content, encoding='utf-8')
        print("Successfully added inventory_stock_management view")
    else:
        print("Could not find inventory_list function to insert before")

if __name__ == "__main__":
    add_inventory_stock_management_view()
