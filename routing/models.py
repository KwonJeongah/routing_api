from django.db import models

# Create your models here.
class Waypoint(models.Model):
    w_id = models.IntegerField(default = -1)
    name = models.CharField(max_length = 200)
    lat = models.FloatField(default = 0)
    lon = models.FloatField(default = 0)
    weight = models.IntegerField(default = 0)
    

class Vehicle(models.Model):
    v_id = models.IntegerField(default = -1)
    capacity = models.IntegerField(default = -1)

    