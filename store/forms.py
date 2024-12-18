# forms.py
from django import forms
from .models import CustomUser, BetSlip
from .models import AviatorBet


class CustomUserCreationForm(forms.ModelForm):
    phone_number = forms.CharField(max_length=15, required=True, label="Phone Number")
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'}),
        label="Password",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
        label="Confirm Password",
    )

    class Meta:
        model = CustomUser
        fields = ('phone_number', 'password')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash the password
        if commit:
            user.save()
        return user

class BetSlipForm(forms.ModelForm):
    class Meta:
        model = BetSlip
        fields = ['bet_amount', 'total_odds', 'bet_data']  # Only fields for this form

class AviatorBetForm(forms.ModelForm):
    class Meta:
        model = AviatorBet
        fields = ['bet_amount']
        widgets = {
            'bet_amount': forms.NumberInput(attrs={
                'placeholder': 'Enter Bet Amount',
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01'
            })
        }
        labels = {
            'bet_amount': 'Bet Amount'
        }
