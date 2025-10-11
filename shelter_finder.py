import requests
import math
from typing import List, Dict

class ShelterFinder:
    """
    Finds potential emergency shelters near coastal areas using OpenStreetMap Overpass API
    """
    
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def get_shelters_near_location(self, lat: float, lon: float, radius_km: float = 5) -> List[Dict]:
        """
        Fetch potential emergency shelters within radius_km of the given coordinates
        """
        
        # Calculate bounding box
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
        
        bbox = f"{lat - lat_delta},{lon - lon_delta},{lat + lat_delta},{lon + lon_delta}"
        
        # Overpass QL query to find potential shelters
        overpass_query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="hospital"]({bbox});
          way["amenity"="hospital"]({bbox});
          node["amenity"="school"]({bbox});
          way["amenity"="school"]({bbox});
          node["amenity"="community_centre"]({bbox});
          way["amenity"="community_centre"]({bbox});
          node["amenity"="social_facility"]({bbox});
          way["amenity"="social_facility"]({bbox});
          node["amenity"="place_of_worship"]({bbox});
          way["amenity"="place_of_worship"]({bbox});
          node["amenity"="townhall"]({bbox});
          way["amenity"="townhall"]({bbox});
          node["building"="civic"]({bbox});
          way["building"="civic"]({bbox});
        );
        out center;
        """
        
        try:
            response = requests.post(
                self.overpass_url,
                data={'data': overpass_query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            shelters = []
            seen_locations = set()
            
            for element in data.get('elements', []):
                # Get coordinates
                if element['type'] == 'node':
                    shelter_lat = element['lat']
                    shelter_lon = element['lon']
                elif 'center' in element:
                    shelter_lat = element['center']['lat']
                    shelter_lon = element['center']['lon']
                else:
                    continue
                
                # Calculate actual distance
                distance = self.haversine_distance(lat, lon, shelter_lat, shelter_lon)
                
                # Only include if within radius and not duplicate
                location_key = f"{shelter_lat:.4f},{shelter_lon:.4f}"
                if distance <= radius_km and location_key not in seen_locations:
                    seen_locations.add(location_key)
                    
                    tags = element.get('tags', {})
                    amenity = tags.get('amenity', 'building')
                    
                    # Determine shelter type and icon
                    shelter_type, icon = self._get_shelter_type_and_icon(amenity, tags)
                    
                    # Get name or generate one
                    name = tags.get('name', f"{shelter_type.title()} Facility")
                    
                    # Estimate capacity based on type
                    capacity = self._estimate_capacity(amenity, tags)
                    
                    # Determine facilities available
                    facilities = self._determine_facilities(amenity, tags)
                    
                    # Generate address
                    address = self._generate_address(tags, shelter_lat, shelter_lon)
                    
                    shelter = {
                        'name': name,
                        'address': address,
                        'lat': shelter_lat,
                        'lon': shelter_lon,
                        'capacity': capacity,
                        'distance': f"{distance:.1f}",
                        'phone': tags.get('phone', 'Contact local authorities'),
                        'icon': icon,
                        'facilities': facilities,
                        'type': shelter_type
                    }
                    
                    shelters.append(shelter)
            
            # Sort by distance
            shelters.sort(key=lambda x: float(x['distance']))
            
            # Limit to top 12 shelters to avoid clutter
            return shelters[:12]
            
        except Exception as e:
            print(f"Error fetching shelters: {e}")
            return []
    
    def _get_shelter_type_and_icon(self, amenity: str, tags: Dict) -> tuple:
        """Determine shelter type and appropriate icon"""
        type_map = {
            'hospital': ('Hospital', 'hospital'),
            'school': ('School', 'school'),
            'community_centre': ('Community Center', 'building'),
            'social_facility': ('Social Facility', 'hands-helping'),
            'place_of_worship': ('Religious Center', 'church'),
            'townhall': ('Town Hall', 'landmark'),
        }
        
        if amenity in type_map:
            return type_map[amenity]
        
        if tags.get('building') == 'civic':
            return ('Civic Building', 'building')
        
        return ('Emergency Shelter', 'home')
    
    def _estimate_capacity(self, amenity: str, tags: Dict) -> str:
        """Estimate capacity based on building type"""
        if 'capacity' in tags:
            return f"{tags['capacity']} people"
        
        if 'beds' in tags:
            return f"{tags['beds']} beds"
        
        capacity_map = {
            'hospital': '200-500 people',
            'school': '300-800 people',
            'community_centre': '150-400 people',
            'place_of_worship': '100-300 people',
            'townhall': '100-250 people',
            'social_facility': '50-150 people',
        }
        
        return capacity_map.get(amenity, '100-200 people')
    
    def _determine_facilities(self, amenity: str, tags: Dict) -> List[str]:
        """Determine available facilities based on shelter type"""
        base_facilities = ['Shelter', 'Emergency Services']
        
        facility_map = {
            'hospital': ['Medical Care', 'Emergency Room', 'Doctors'],
            'school': ['Large Space', 'Toilets', 'Kitchen'],
            'community_centre': ['Meeting Rooms', 'Kitchen', 'Toilets'],
            'place_of_worship': ['Large Hall', 'Kitchen', 'Parking'],
            'townhall': ['Meeting Rooms', 'Offices', 'Parking'],
            'social_facility': ['Support Services', 'Counseling', 'Aid'],
        }
        
        specific = facility_map.get(amenity, ['Basic Amenities'])
        return base_facilities + specific[:3]
    
    def _generate_address(self, tags: Dict, lat: float, lon: float) -> str:
        """Generate address from tags or coordinates"""
        addr_parts = []
        
        if 'addr:street' in tags:
            street = tags['addr:street']
            if 'addr:housenumber' in tags:
                addr_parts.append(f"{tags['addr:housenumber']} {street}")
            else:
                addr_parts.append(street)
        
        if 'addr:city' in tags:
            addr_parts.append(tags['addr:city'])
        elif 'addr:suburb' in tags:
            addr_parts.append(tags['addr:suburb'])
        
        if addr_parts:
            return ', '.join(addr_parts)
        
        return f"Near {lat:.4f}°, {lon:.4f}°"