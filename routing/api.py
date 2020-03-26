from .models import Waypoint, Vehicle
from rest_framework import serializers, viewsets

class WaypointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waypoint
        fields = '__all__'

class WaypointViewSet(viewsets.ModelViewSet):
    queryset = Waypoint.objects.all()
    serializer_class = WaypointSerializer

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer