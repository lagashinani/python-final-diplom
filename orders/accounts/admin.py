from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Contact, ConfirmEmailToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'company', 'position')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined'),}),
        (_('Groups'), {'fields': ('groups',)}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    pass


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'key',)
