from django.db import models as models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
from django.db.models import UniqueConstraint
from simple_history.models import HistoricalRecords
from typing import Dict, List

# Ability to add a timestamp to any model instance
class TimeStampedModelInstance(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


# Location of an NES-LTER station at a given time
class StationLocation(TimeStampedModelInstance):
    geolocation = gis_models.PointField()
    depth = models.FloatField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    def get_station(self):
        return self.content_object
    
    def __str__(self):
        return '{}: {} {}'.format(self.content_object, self.geolocation.y, self.geolocation.x)


# Station model with locations
class Station(models.Model):
    name = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    locations = GenericRelation(StationLocation, related_query_name='station')

    def set_location(self, latitude, longitude, start_time, end_time=None, depth=None, comment=None):
        if end_time is not None:
            if end_time == start_time:
                raise ValueError('start and end time must not be identical')
            elif end_time < start_time:
                raise ValueError('end_time must be greater than or equal to start_time')
        
        if self.locations.filter(start_time=start_time).exists():
            raise ValueError('A location already exists at the given start_time')

        # Create a new Point object for the geolocation
        geolocation = Point(longitude, latitude, srid=4326)
 
        # If less recent, set the end_time to the start_time of the successor location
        successor = self.locations.filter(start_time__gt=start_time).order_by('start_time').first()

        if successor is not None:
            if end_time is None:
                end_time = successor.start_time
            if end_time > successor.start_time:
                raise ValueError('end_time must be less than or equal to the start_time of the successor location')
            
        # If more recent, close any currently "open" (end_time is None) locations by setting their end_time to the new start_time
        self.locations.filter(start_time__lt=start_time).filter(end_time__isnull=True).update(end_time=start_time)

        # Create a new StationLocation linked to this Station
        StationLocation.objects.create(
            content_object=self,
            geolocation=geolocation,
            depth=depth,
            start_time=start_time,
            end_time=end_time,
            comment=comment
        )

    def get_location(self, timestamp=None):
        if timestamp is None:
            timestamp = timezone.now()

        locations = self.locations.filter(
            Q(end_time__gte=timestamp) | Q(end_time__isnull=True),
            start_time__lte=timestamp
        ).order_by('-start_time')

        if locations.exists():
            return locations.first()
        else:
            return None

    @classmethod
    def get_locations(cls, timestamp=None):
        if timestamp is None:
            timestamp = timezone.now()

        locations = []

        for station in cls.objects.all():
            location = station.get_location(timestamp)
            if location is not None:
                locations.append(location)

        return locations
    
    @classmethod
    def distances(cls, latitude, longitude, timestamp):
        from django.contrib.gis.db.models.functions import Distance

        # Create a Point object from the latitude and longitude
        geolocation = Point(longitude, latitude, srid=4326)

        return StationLocation.objects.filter(
            Q(end_time__gte=timestamp) | Q(end_time__isnull=True),
            start_time__lte=timestamp
        ).annotate(distance=Distance('geolocation', geolocation)).order_by('distance')


    @classmethod
    def nearest_location(cls, latitude, longitude, timestamp=None):
        if timestamp is None:
            timestamp = timezone.now()

        distances = cls.distances(latitude, longitude, timestamp)

        if distances.exists():
            return distances.first()
        else:
            return None
        

    @classmethod
    def add_nearest_station(cls, latitude, longitude, timestamp):
        nearest_station_name = []
        nearest_station_distance = []
        for latitude, longitude, timestamp in zip(latitude, longitude, timestamp):
            location = cls.nearest_location(latitude, longitude, timestamp)
            if location is not None:
                nearest_station_name.append(location.content_object.name)
                nearest_station_distance.append(location.distance.km)
            else:
                nearest_station_name.append(None)
                nearest_station_distance.append(None)
        return nearest_station_name, nearest_station_distance


    def __str__(self):
        return self.name


class Vessel(models.Model):
    designation = models.CharField(max_length=32) # e.g., "R/V"
    name = models.CharField(max_length=100, unique=True) # e.g., "Neil Armstrong"
    short_name = models.CharField(max_length=32, unique=True) # e.g., "Armstrong"
    code = models.CharField(max_length=32, unique=True) # e.g., "AR"

    def __str__(self):
        return self.name
    

class Cruise(models.Model):
    class CruiseType(models.TextChoices):
        NESLTER = "NESLTER"
        JP_STUDENT = "JP Student"
        MAB_PIONEER = "MAB Pioneer"

    name = models.CharField(max_length=100, unique=True) # e.g. "EN627"
    vessel = models.ForeignKey(Vessel, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=32,
        choices=CruiseType.choices,
        default=CruiseType.NESLTER
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
    

class Cast(models.Model):
    cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, related_name='casts')
    number = models.CharField(max_length=32) # string to handle cases like "5a"
    depth = models.FloatField() # nominal depth
    geolocation = gis_models.PointField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        constraints = [
            UniqueConstraint(fields=['cruise', 'number'], name='unique_cruise_cast_number')
        ]

    def __str__(self):
        return '{} cast {}'.format(self.cruise, self.number)


class Niskin(models.Model):
    cast = models.ForeignKey(Cast, on_delete=models.CASCADE, related_name='niskins')
    number = models.PositiveIntegerField()
    depth = models.FloatField()
    geolocation = gis_models.PointField(null=True, blank=True)
    
    class Meta:
        constraints = [
            UniqueConstraint(fields=['cast', 'number'], name='unique_cast_niskin_number')
        ]

    def __str__(self):
        return '{} niskin {}'.format(self.cast, self.number)


class Event(models.Model):
    cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, related_name='events')
    r2r_event = models.CharField(max_length=30, null=True, blank=True)
    message_id = models.IntegerField(null=True)
    instrument = models.CharField(max_length=100)
    action = models.CharField(max_length=32)
    station = models.CharField(max_length=100)
    cast = models.CharField(max_length=32)
    comment = models.CharField(max_length=500)
    geolocation = gis_models.PointField()
    datetime = models.DateTimeField()
    history = HistoricalRecords()
    
    class Meta:
        constraints = [
            UniqueConstraint(fields=['cruise', 'r2r_event'], name='unique_cruise_r2r_event')
        ]

    def __str__(self):
        return '{} event {}'.format(self.cruise, self.r2r_event)

class Underway(models.Model):
    cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, related_name='underway')
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.cruise)


class HPLC(models.Model):    
    
    MAPPINGS: Dict[str, str] = {
        "Cruise ID": "cruise",
        "cruise" : "cruise",
        "Unnamed: 1": "date",
        "Latitude": "latitude",
        "lat": "latitude",
        "Longitude": "longitude",
        "lon": "longitude",
        "Sampling Depth (meters)": "depth",
        "Station": "cast",
        "station": "cast",
        "Bottle Number": "niskin",
        "bottle" : "niskin",
        "Sample Label": "sample_id",
        "sample": "sample_id",
        "GSFC Lab sample code": "alternate_sample_id",
        "hplc_gsfc_id": "alternate_sample_id",
        "Unnamed: 9": "project_id",
        "Unnamed: 10": "replicate",
        "Volume filtered (ml)": "vol_filtered",
        "volfilt": "vol_filtered",
        "[Tot_Chl_a]": "Tot_Chl_a",
        "[Tot_Chl_b]": "Tot_Chl_b",
        "[Tot_Chl_c]": "Tot_Chl_c",
        "[Alpha_beta_Car]": "alpha-beta-Car",
        "Alpha-beta-Car": "alpha-beta-Car",
        "[But fuco]": "But-fuco",
        "[Hex fuco]": "Hex-fuco",
        "[Allo]": "Allo",
        "[Diadino]": "Diadino",
        "[Diato]": "Diato",
        "[Fuco]": "Fuco",
        "[Perid]": "Perid",
        "[Zea]": "Zea",
        "[MV_Chl_a]": "MV_Chl_a",
        "[DV_Chl_a]": "DV_Chl_a",
        "[Chlide_a]": "Chlide_a",
        "[MV_Chl _b]": "MV_Chl_b",
        "MV_Chl _b": "MV_Chl_b",
        "[DV_Chl_b]": "DV_Chl_b",
        "[Chl c1c2]": "Chl_c1c2",
        "[Chl_c3]": "Chl_c3",
        "[Lut]": "Lut",
        "[Neo]": "Neo",
        "[Viola]": "Viola",
        "[Phytin_a]": "Phytin_a",
        "[Phide_a]": "Phide_a",
        "[Pras]": "Pras",
        "[Gyro]": "Gyro",
        "[TChl]": "TChl",
        "Tchl": "TChl",
        "[PPC]": "PPC",
        "[PSC]": "PSC",
        "[PSP]": "PSP",
        "[TCar]": "TCar",
        "Tcar": "TCar",
        "[TAcc]": "TAcc",
        "Tacc": "TAcc",
        "[TPg]": "TPg",
        "Tpg": "TPg",
        "[DP]": "DP",
        "[TAcc]/[Tchla]": "TAcc_TChla",
        "Tacc_Tchla": "TAcc_TChla",
        "[PSC]/[TCar]": "PSC_TCar",
        "PSC_Tcar": "PSC_TCar",
        "[PPC]/[TCar]": "PPC_TCar",
        "PPC_Tcar": "PPC_TCar",
        "[TChl]/[TCar]": "TChl_TCar",
        "Tchl_Tcar": "TChl_TCar",
        "[PPC]/[Tpg]": "PPC_TPg",
        "PPC_Tpg": "PPC_TPg",
        "[PSP]/[TPg]": "PSP_TPg",
        "PSP_Tpg": "PSP_TPg",
        "[TChl a]/[TPg]": "TChla_Tpg",
        "Tchl a_Tpg": "TChla_Tpg",
        "comments": "comments",
        "other": "comments2",
        "other.1": "comments3",
        "Indicate if filters are replicates": "R",     
        "indicate if filters are replicates": "R"
    }

    COLUMNS: List[str] = [
        "cruise", "date", "latitude", "longitude", "depth", "cast", "niskin",
        "sample_id", "alternate_sample_id", "project_id", "replicate",
        "vol_filtered", "Tot_Chl_a", "Tot_Chl_b", "Tot_Chl_c", "alpha-beta-Car",
        "But-fuco", "Hex-fuco", "Allo", "Diadino", "Diato", "Fuco", "Perid",
        "Zea", "MV_Chl_a", "DV_Chl_a", "Chlide_a", "MV_Chl_b", "DV_Chl_b",
        "Chl_c1c2", "Chl_c3", "Lut", "Neo", "Viola", "Phytin_a", "Phide_a",
        "Pras", "Gyro", "TChl", "PPC", "PSC", "PSP", "TCar", "TAcc", "TPg",
        "DP", "TAcc_TChla", "PSC_TCar", "PPC_TCar", "TChl_TCar", "PPC_TPg",
        "PSP_TPg", "TChla_Tpg", "comments", "comments2", "comments3"
    ]

    @classmethod
    def get_mappings(cls) -> Dict[str, str]:
        return cls.MAPPINGS

    @classmethod
    def get_columns(cls) -> List[str]:
        return cls.COLUMNS

    def __str__(self):
        return f"HPLC Mapping"
