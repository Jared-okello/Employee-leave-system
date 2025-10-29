# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response

class LeaveListAPIView(APIView):
    def get(self, request):
        return Response({"message": "API is working"})