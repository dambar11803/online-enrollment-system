from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    # include is_active so the token becomes invalid once the user is activated
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_active}{timestamp}"


account_activation_token = EmailVerificationTokenGenerator()
