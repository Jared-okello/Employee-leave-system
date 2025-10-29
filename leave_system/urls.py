from os import path
from accounts.views import SignUpView

urlpatterns = [
    # ... existing paths ...
    path('signup/', SignUpView.as_view(), name='signup'),
]