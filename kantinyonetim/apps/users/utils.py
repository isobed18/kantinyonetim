from .models import AuditLog, Notification
from django.utils import timezone

def log_user_action(user, action, resource_type=None, resource_id=None, details=None, request=None):
    """
    Log user actions for audit purposes
    """
    print(f"Attempting to log action: {action}")
    print(f"User: {user.username if user else 'Anonymous'}, Resource Type: {resource_type}, Resource ID: {resource_id}, Details: {details}")
    try:
        ip_address = None
        user_agent = ""
        
        if request:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type or '',
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        print(f"Successfully logged action: {action}")
    except Exception as e:
        # Don't let logging errors break the main functionality
        print(f"Logging error: {e}")

def get_client_ip(request):
    """
    Get client IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def create_notification(recipient, notification_type, title, message, priority='medium', 
                       resource_type=None, resource_id=None):
    """
    Create a notification for a user
    """
    try:
        Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            resource_type=resource_type or '',
            resource_id=resource_id
        )
    except Exception as e:
        print(f"Notification creation error: {e}")

def notify_staff_new_order(order, customer):
    """
    Notify all staff and admin users about a new order
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    staff_users = User.objects.filter(role__in=['staff', 'admin'])
    
    for staff_user in staff_users:
        create_notification(
            recipient=staff_user,
            notification_type='order_new',
            title='New Order Received',
            message=f'Customer {customer.username} has placed a new order #{order.id}',
            priority='high',
            resource_type='order',
            resource_id=order.id
        )

def notify_order_status_change(order, old_status, new_status, changed_by, request=None):
    """
    Notify relevant users about order status changes
    """
    # Notify customer about status change
    create_notification(
        recipient=order.user,
        notification_type='order_status',
        title='Order Status Updated',
        message=f'Your order #{order.id} status changed from {old_status} to {new_status}',
        priority='medium',
        resource_type='order',
        resource_id=order.id
    )
    
    # Log the status change
    log_user_action(
        user=changed_by,
        action='order_status_changed',
        resource_type='order',
        resource_id=order.id,
        details={
            'order_id': order.id,
            'old_status': old_status,
            'new_status': new_status,
            'customer': order.user.username
        },
        request=request # Pass request object for full audit details
    )
