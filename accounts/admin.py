from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .forms import UserCreationForm, UserChangeForm


class UserAdmin(BaseUserAdmin):
    model = User
    add_form = UserCreationForm
    form = UserChangeForm

    list_display = ('phone', 'user_type', 'credit', 'traccar_id', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active', 'is_superuser')
    search_fields = ('phone', 'first_name', 'last_name')
    ordering = ('phone',)

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('User Type', {'fields': ('user_type',)}),  # New section for user type
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Credit Info', {'fields': ('credit',)}),
        ('Traccar Info', {'fields': ('traccar_token', 'traccar_id')}),
        ('Change Password', {'fields': ('password1', 'password2')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'user_type', 'credit', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    # Custom actions for bulk user type changes
    actions = ['make_customer', 'make_support', 'make_admin']

    @admin.action(description='تغییر به مشتری')
    def make_customer(self, request, queryset):
        updated = queryset.update(user_type='customer')
        self.message_user(request, f'{updated} کاربر به مشتری تغییر یافت.')

    @admin.action(description='تغییر به پشتیبانی')
    def make_support(self, request, queryset):
        updated = queryset.update(user_type='support')
        self.message_user(request, f'{updated} کاربر به پشتیبانی تغییر یافت.')

    @admin.action(description='تغییر به مدیر')
    def make_admin(self, request, queryset):
        updated = queryset.update(user_type='admin')
        self.message_user(request, f'{updated} کاربر به مدیر تغییر یافت.')


admin.site.register(User, UserAdmin)