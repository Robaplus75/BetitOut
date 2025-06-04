from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()

class Bet(models.Model):
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_bets"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    winner_option = models.ForeignKey(
        'BetOption',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='winning_bets'
    )
    judge = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='judged_bets'
    )

    def resolve(self, winner_option):
        if self.is_resolved:
            raise ValidationError("Bet is already resolved.")
        if winner_option not in self.options.all():
            raise ValidationError("Winner option must belong to this bet.")

        self.winner_option = winner_option
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()


    def clean(self):
        if self.options.count() < 2:
            raise ValidationError("A bet must have at least two options.")
        if len(set(option.text for option in self.options.all())) != len(self.options.all()):
            raise ValidationError("Bet options must be unique.")

    def __str__(self):
        return f"{self.title} ({self.creator.username})"

class BetOption(models.Model):
    bet = models.ForeignKey(
        Bet,
        on_delete=models.CASCADE,
        related_name='options'
    )
    text = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.text} (Bet: {self.bet.title})"


class BetParticipant(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="joined_bets"
    )
    bet = models.ForeignKey(
        Bet,
        on_delete=models.PROTECT,
        related_name="participants"
    )
    stake = models.DecimalField(max_digits=10, decimal_places=2)
    chosen_option = models.ForeignKey(
        BetOption,
        on_delete=models.PROTECT,
        related_name="participants"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'bet')

    def clean(self):
        if self.chosen_option.bet_id != self.bet_id:
            raise ValidationError("The chosen option does not belong to the selected bet.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} chose {self.chosen_option.text} for ${self.stake} on {self.bet.title}"


