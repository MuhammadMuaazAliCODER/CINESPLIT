from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdministrator, IsAuthenticatedUser
from .serializers import DashboardSerializer
from .services import dashboard_data


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_dashboard", responses={200: DashboardSerializer})
    def get(self, request):
        return Response(dashboard_data())
