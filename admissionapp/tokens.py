from django.contrib.auth.tokens import PasswordResetTokenGenerator 
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str


# tokens.py

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Include is_active so token invalidates after activation
        return f"{user.pk}{timestamp}{user.is_active}"

account_activation_token = AccountActivationTokenGenerator()

