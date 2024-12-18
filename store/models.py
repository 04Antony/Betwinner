from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, User 
from django.contrib.auth import get_user_model
from django.utils.timezone import now
import uuid
from decimal import Decimal
import random


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None):
        if not phone_number:
            raise ValueError('Users must have a phone number')
        user = self.model(phone_number=phone_number)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None):
        user = self.create_user(phone_number, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Required by Django admin
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # User account balance

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number

def get_default_user():
    User = get_user_model()
    # Ensure this returns a valid ID or None
    user = User.objects.first()
    return user.id if user else None

class Bet(models.Model):
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    outcome = models.CharField(max_length=50)
    odds = models.FloatField()

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - {self.outcome} ({self.odds})"


# Model to represent a user's betslip
class BetSlip(models.Model):

# Link each betslip to a user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE,related_name="betslips")
    

    bet_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_odds = models.FloatField()
    bet_data = models.JSONField()  # Store bets in JSON format
    
    def __str__(self):
        return f"Bet Amount: {self.bet_amount}, Total Odds: {self.total_odds}"

    def save_bets(self, betslip_data):
        """Helper method to save the individual bets from the betslip"""
        self.bet_data = betslip_data
        self.save()


class AviatorGame(models.Model):
    """Represents a single Aviator game round."""
    crash_point = models.FloatField(null=True)
    round_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4, blank=False) # Unique identifier for the game round
    start_time = models.DateTimeField(default=now)  # When the round starts
    end_time = models.DateTimeField(null=True, blank=True)
    crash_multiplier = models.FloatField(default=1.0)  # Multiplier at which the plane crashes
    is_active = models.BooleanField(default=True)  # Indicates if the game round is ongoing
    created_at = models.DateTimeField(auto_now_add=True)

 

    @property
    def current_multiplier(self):
        """Calculate the current multiplier based on the elapsed time."""
        if not self.is_active or self.crash_point <= 0:
            return None  # Game is not active or invalid crash point

        elapsed_time = (now() - self.start_time).total_seconds()
        multiplier = 0.02 + elapsed_time * 0.05  # Example growth rate: 0.1 per second
        return round(min(multiplier, self.crash_point), 2)

    def is_multiplier_active(self):
        """Check if the multiplier is still moving."""
        return self.is_active and self.current_multiplier and self.current_multiplier < self.crash_point

    def __str__(self):
        return f"Round {self.round_id} - Crash Multiplier: {self.crash_multiplier}"
    

class AviatorBet(models.Model):
    """Represents a user's bet in the Aviator game."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aviator_bets")
    game = models.ForeignKey( AviatorGame, on_delete=models.CASCADE, related_name="bets", null=True, blank=False)
    bet_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount the user bets
    cash_out_multiplier = models.FloatField(null=True, blank=True)  # Multiplier at which the user cashed out
    winnings = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Calculated winnings
    cashed_out_at = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_cashed_out = models.BooleanField(default=False)  # Whether the user cashed out
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_active'],
                condition=models.Q(is_active=True),
                name='unique_active_bet_per_user'
            )
        ]

    def __str__(self):
        return f"Bet by {self.user} - Active: {self.is_active}"

    def calculate_winnings(self):
        """Calculate and return winnings based on cash-out multiplier."""
        if self.is_cashed_out and self.cash_out_multiplier:
               return self.bet_amount * Decimal(self.cash_out_multiplier)
        return 0

    def save(self, *args, **kwargs):
        """Override save to calculate winnings if cashed out."""
        if self.is_cashed_out and self.cash_out_multiplier:
            self.winnings = self.calculate_winnings()
        super().save(*args, **kwargs)

    def __str__(self):
        cash_out_status = "Cashed Out" if self.is_cashed_out else "Not Cashed Out"
        return f"User {self.user.phone_number} - {cash_out_status} - Bet: {self.bet_amount}"
    def __str__(self):
        return f"Bet {self.id} by {self.user}"

class AviatorRoundSummary(models.Model):
    """Keeps a summary of each Aviator round, including results and user performance."""
    game = models.OneToOneField(AviatorGame, on_delete=models.CASCADE, related_name="summary")
    total_bets = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Sum of all bets in the round
    total_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Total payout for the round
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Round {self.game.round_id} - Bets: {self.total_bets} - Payout: {self.total_payout}"

    def update_summary(self):
        """Calculate total bets and payouts for the round."""
        bets = self.game.bets.all()
        self.total_bets = sum(bet.bet_amount for bet in bets)
        self.total_payout = sum(bet.winnings for bet in bets if bet.is_cashed_out)
        self.save()
    def save(self, *args, **kwargs):
        if not self.game or not self.game.is_active:
            raise ValueError("Bet must be associated with an active game.")
        super().save(*args, **kwargs)

class GameAnalytics(models.Model):
    game = models.OneToOneField(AviatorGame, on_delete=models.CASCADE, related_name="analytics")
    average_cash_out_multiplier = models.FloatField(null=True, blank=True)
    most_common_multiplier = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Leaderboard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_winnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    games_played = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
