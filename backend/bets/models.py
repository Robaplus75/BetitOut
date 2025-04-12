from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Bet(models.Model):
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_bets"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    option_one = models.CharField(max_length=100)
    option_two = models.CharField(max_length=100)
    stake = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_resolved = models.BooleanField(default=False)
    winner_option = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.creator.username})"


class BetParticipant(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="joined_bets"
    )
    bet = models.ForeignKey(
        Bet,
        on_delete=models.CASCADE,
        related_name="participants"
    )
    chosen_option = models.CharField(max_length=100)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'bet')

    def __str__(self):
        return f"{self.user.username} chose {self.chosen_option} on {self.bet.title}"


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} — ${self.balance}"

