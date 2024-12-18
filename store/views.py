from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm
from .forms import BetSlipForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import BetSlip
from django.http import JsonResponse, Http404
import json
from django.views import View
from .models import Bet
from decimal import Decimal
from .models import AviatorGame, AviatorBet
from .forms import AviatorBetForm
from django.utils.timezone import now
import uuid
from django.db import transaction
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
import random
from datetime import datetime



# Create your views here.

def home(request):
    return render(request, "store/index.html")


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to a login page or another page after registration
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/auth/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        
        # Authenticate the user
        user = authenticate(request, username=phone_number, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # Redirect to a homepage or dashboard after login
        else:
            messages.error(request, "Invalid phone number or password")
    
    return render(request, 'store/auth/login.html')
@login_required
def submit_betslip(request):
    if request.method == "POST":
        # Parse JSON data from the form
        betslip_data = request.POST.get("betslip_data")
        bet_amount = request.POST.get("bet_amount")
        total_odds = request.POST.get("total_odds")
        
        # Check if data is present
        if not (betslip_data and bet_amount and total_odds):
            return render(request, 'store/submit_betslip.html', {'error': 'Missing data in the form.'})
        
        # Convert betslip_data to Python dictionary
        try:
            betslip_data = json.loads(betslip_data)
        except json.JSONDecodeError:
            return render(request, 'store/submit_betslip.html', {'error': 'Invalid betslip data format.'})

        # Check if bet_amount is a valid number
        try:
            bet_amount = Decimal(bet_amount) 
        except ValueError:
            return render(request, 'store/submit_betslip.html', {'error': 'Invalid bet amount.'})

        # Ensure bet amount is at least the minimum and user has sufficient balance
        MIN_BET_AMOUNT = 5
        if bet_amount < MIN_BET_AMOUNT:
            return render(request, 'store/submit_betslip.html', {'error': f'Minimum bet amount is {MIN_BET_AMOUNT}.'})
        
        user_balance = request.user.balance  # Assuming `CustomUser` model has a `balance` field
        if user_balance < bet_amount:
            return render(request, 'store/submit_betslip.html', {'error': 'Insufficient balance to place this bet.'})
        
        # Populate form with data
        form_data = {
            'bet_amount': bet_amount,
            'total_odds': total_odds,
            'bet_data': betslip_data,  # Assuming your BetSlip model has a JSONField named `bet_data`
        }
        form = BetSlipForm(form_data)

        if form.is_valid():
            # Deduct the bet amount from the user's balance
            request.user.balance -= bet_amount
            request.user.save()

            betslip = form.save(commit=False)
            betslip.user = request.user  # Link betslip to the current user
            betslip.save()

            # Optionally, clear the betslip data from localStorage after saving (handled on frontend)
            return redirect('bet_confirmation')  # Redirect to confirmation page or similar
        else:
            return render(request, 'store/submit_betslip.html', {'form': form, 'error': 'Form validation failed.'})
    else:
        form = BetSlipForm()

    return render(request, 'store/submit_betslip.html', {'form': form})
@login_required  # Ensure only logged-in users can submit
def bet_confirmation(request):
    return render(request, 'store/bet_confirmation.html')
@login_required  # Ensure only logged-in users can submit
def my_bets(request):
    betslips = BetSlip.objects.filter(user=request.user)  # Get bets for the logged-in user

    # Add calculations to each betslip
    for betslip in betslips:
        # Ensure both bet_amount and total_odds are of type Decimal
        bet_amount = Decimal(betslip.bet_amount)  # Make sure bet_amount is Decimal
        total_odds = Decimal(betslip.total_odds)  # Convert total_odds to Decimal if it's not

        possible_win = bet_amount * total_odds
        withholding_tax = possible_win * Decimal('0.15')  # 15% tax
        payout = possible_win - withholding_tax

        # Store these values for use in the template
        betslip.possible_win = possible_win
        betslip.withholding_tax = withholding_tax
        betslip.payout = payout

    return render(request, 'store/my_bets.html', {'betslips': betslips})
@login_required
def aviator(request):
    return render(request, 'store/aviator.html')
@login_required  # Ensure only logged-in users can submit
def account(request):
    return render(request, 'store/account.html')


def homepage(request):
    # Pass the user's balance if they are authenticated
    context = {
        'user_balance': request.user.balance if request.user.is_authenticated else 0
    }
    return render(request, 'homepage.html', context)
@csrf_exempt
@login_required
def place_bet(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            bet_amount = data.get("bet_amount")

            if not bet_amount or bet_amount <= 0:
                return JsonResponse({"success": False, "error": "Invalid bet amount."}, status=400)

            user = request.user

            # Check if user has enough balance
            if user.balance < bet_amount:
                return JsonResponse({"success": False, "error": "Insufficient balance."}, status=400)

            # Ensure there's an active game
            game = auto_activate_game()

            # Deduct bet amount from user's balance
            user.balance -= bet_amount
            user.save()

            # Create the bet
            aviator_bet = AviatorBet.objects.create(
                user=user,
                bet_amount=bet_amount,
                game=game,  # Associate bet with the active game
                is_active=True,  # Mark the bet as active
            )

            return JsonResponse({"success": True, "bet_id": aviator_bet.id})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)


def start_new_game():
    # Mark all existing games as inactive
    AviatorGame.objects.filter(is_active=True).update(is_active=False)
    # Create and start a new game
    new_game = AviatorGame.objects.create()
    return new_game



def end_game_round():
    active_game = AviatorGame.objects.filter(is_active=True).first()
    if active_game:
        active_game.end_game()


@login_required
def cash_out(request, bet_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=400)

    # Ensure there's an active game
    game = auto_activate_game()

    # Fetch the bet
    try:
        bet = AviatorBet.objects.get(id=bet_id, user=request.user, is_active=True)
    except AviatorBet.DoesNotExist:
        return JsonResponse({"error": "Bet not found or already cashed out."}, status=400)


    # Ensure multiplier is active
    if not game.is_multiplier_active():
        return JsonResponse({"error": "Multiplier is not active or game has ended."}, status=400)

    # Perform cashout
    current_multiplier = game.current_multiplier
    bet.cash_out_multiplier = current_multiplier
    bet.is_cashed_out = True
    bet.is_active = False
    bet.save()

    return JsonResponse({
        "success": True,
        "winnings": bet.calculate_winnings(),
        "cash_out_multiplier": current_multiplier
    })
def auto_activate_game():
    """Ensure there's always an active Aviator game."""
    active_game = AviatorGame.objects.filter(is_active=True).first()

    # Check if there's an active game or if it's multiplier inactive
    if not active_game or not active_game.is_multiplier_active():
        # Deactivate all other games
        AviatorGame.objects.filter(is_active=True).update(is_active=False)

        # Create a new game
        crash_point = random.uniform(1.5, 5.0)  # Random crash point
        new_game = AviatorGame.objects.create(
            is_active=True,
            crash_point=crash_point,
            start_time=now(),
        )
        return new_game
    return active_game

def activate_game():
    """Deactivate existing games and create a new one with a random crash point."""
    try:
        with transaction.atomic():
            # Deactivate all active games
            AviatorGame.objects.filter(is_active=True).update(is_active=False)

            # Generate a unique round ID and random crash point
            round_id = str(uuid.uuid4())
            crash_point = Decimal(str(round(random.uniform(1.01, 10.0), 2)))

            # Create the new game
            new_game = AviatorGame.objects.create(
                round_id=round_id,
                crash_point=crash_point,
                is_active=True,
                start_time=now(),
            )
            return new_game
    except Exception as e:
        print(f"Error activating game: {e}")
        return None

def get_active_game(request):
    """Retrieve the current active game as JSON."""
    game = AviatorGame.objects.filter(is_active=True).first()
    if game:
        return JsonResponse({
            "round_id": game.round_id,
            "crash_point": float(game.crash_point),  # Convert Decimal to float for JSON
            "start_time": game.start_time,
            "current_multiplier": game.current_multiplier,
        })
    return JsonResponse({"error": "No active game found."}, status=404)