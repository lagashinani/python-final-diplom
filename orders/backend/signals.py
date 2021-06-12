from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from accounts.models import User, ConfirmEmailToken
from .tasks import send_email


new_user_registered = Signal(
    providing_args=['user_id'],
)

new_order = Signal(
    providing_args=['user_id'],
)


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    отправляем письмо с токеном для сброса пароля
    """
    # send an e-mail to the user
    title = f'Сброс пароля для {reset_password_token.user}'
    message = f'Токен для сброса пароля {reset_password_token.key}'
    email = reset_password_token.user
    send_email(title, message, email)


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    """
    отправляем письмо с подтрердждением почты
    """
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)
    title = f'Подтверждение регистрации для {token.user.email}'
    message = f'Токен для подтверждения регистрации {token.key}'
    email = token.user.email
    send_email(title, message, email)


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    отправяем письмо при изменении статуса заказа
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)
    title = 'Обновление статуса заказа'
    message = 'Заказ сформирован'
    email = user.email
    send_email.apply_async((title, message, email), countdown=5 * 60)
