from django import forms


class CheckoutForm(forms.Form):
    full_name = forms.CharField(min_length=3, max_length=80)
    email = forms.EmailField()
    phone = forms.CharField(min_length=7, max_length=24)
    city = forms.CharField(max_length=60)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), min_length=8)
    payment_method = forms.ChoiceField(
        choices=[
            ("card", "Credit / debit card"),
            ("cash", "Cash on delivery"),
            ("transfer", "Bank transfer"),
        ]
    )

    UZ_LABELS = {
        "full_name": "To'liq ism",
        "email": "Email",
        "phone": "Telefon",
        "city": "Shahar",
        "address": "Manzil",
        "payment_method": "To'lov usuli",
    }
    UZ_PAYMENT_CHOICES = [
        ("card", "Karta orqali"),
        ("cash", "Yetkazilganda naqd"),
        ("transfer", "Bank o'tkazmasi"),
    ]

    def __init__(self, *args, language="en", **kwargs):
        super().__init__(*args, **kwargs)
        if language == "uz":
            for name, label in self.UZ_LABELS.items():
                self.fields[name].label = label
            self.fields["payment_method"].choices = self.UZ_PAYMENT_CHOICES

    def clean_phone(self):
        phone = self.cleaned_data["phone"].replace(" ", "")
        allowed = set("0123456789+-()")
        if any(char not in allowed for char in phone):
            raise forms.ValidationError("Enter a valid phone number.")
        digits = [char for char in phone if char.isdigit()]
        if len(digits) < 7:
            raise forms.ValidationError("Enter a valid phone number.")
        return phone


class ReviewForm(forms.Form):
    name = forms.CharField(max_length=60)
    rating = forms.ChoiceField(choices=[(str(value), str(value)) for value in range(5, 0, -1)])
    text = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), min_length=5, max_length=600)

    UZ_LABELS = {
        "name": "Ism",
        "rating": "Baho",
        "text": "Sharh",
    }
    EN_PLACEHOLDERS = {
        "name": "Your name",
        "text": "Write your opinion about the product",
    }
    UZ_PLACEHOLDERS = {
        "name": "Ismingiz",
        "text": "Mahsulot haqida fikringizni yozing",
    }

    def __init__(self, *args, language="en", **kwargs):
        super().__init__(*args, **kwargs)
        if language == "uz":
            for name, label in self.UZ_LABELS.items():
                self.fields[name].label = label
            placeholders = self.UZ_PLACEHOLDERS
        else:
            placeholders = self.EN_PLACEHOLDERS
        self.fields["name"].widget.attrs.update({"placeholder": placeholders["name"]})
        self.fields["text"].widget.attrs.update({"placeholder": placeholders["text"]})
