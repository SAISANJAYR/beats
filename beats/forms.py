from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Song, Rating


class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['title', 'artist', 'album', 'genre', 'release_year', 'cover_url']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Song title', 'class': 'form-input'}),
            'artist': forms.TextInput(attrs={'placeholder': 'Artist name', 'class': 'form-input'}),
            'album': forms.TextInput(attrs={'placeholder': 'Album (optional)', 'class': 'form-input'}),
            'genre': forms.Select(attrs={'class': 'form-input'}),
            'release_year': forms.NumberInput(attrs={'placeholder': 'e.g. 2024', 'class': 'form-input'}),
            'cover_url': forms.URLInput(attrs={'placeholder': 'https://...', 'class': 'form-input'}),
        }


SCORE_CHOICES = [
    (0.5, '½ ★'),
    (1.0, '1 ★'),
    (1.5, '1½ ★'),
    (2.0, '2 ★'),
    (2.5, '2½ ★'),
    (3.0, '3 ★'),
    (3.5, '3½ ★'),
    (4.0, '4 ★'),
    (4.5, '4½ ★'),
    (5.0, '5 ★'),
]


class RatingForm(forms.ModelForm):
    score = forms.ChoiceField(
        choices=SCORE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'star-radio'}),
        label='Your Rating'
    )

    class Meta:
        model = Rating
        fields = ['score', 'review', 'liked']
        widgets = {
            'review': forms.Textarea(attrs={
                'placeholder': 'Write a review (optional)...',
                'class': 'form-input',
                'rows': 4,
            }),
            'liked': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_score(self):
        return float(self.cleaned_data['score'])


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'placeholder': 'Email address', 'class': 'form-input'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not hasattr(field.widget, 'attrs'):
                continue
            field.widget.attrs.setdefault('class', 'form-input')
