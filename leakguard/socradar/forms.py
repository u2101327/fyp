from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import MonitoredCredential

class CreateUserForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class MonitoredCredentialForm(forms.ModelForm):
    class Meta:
        model = MonitoredCredential
        fields = ['email', 'username', 'domain']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
            'domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter domain name'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        username = cleaned_data.get('username')
        domain = cleaned_data.get('domain')
        
        # At least one field must be provided
        if not any([email, username, domain]):
            raise forms.ValidationError('At least one credential field must be provided.')
        
        return cleaned_data

