"""
SDK Generator for AI Road Trip Storyteller API
Generates client SDKs in multiple languages from OpenAPI specification
"""

import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import textwrap


class SDKGenerator:
    """Generate client SDKs in multiple languages"""
    
    def __init__(self, openapi_spec: Dict[str, Any]):
        self.spec = openapi_spec
        self.info = self.spec.get("info", {})
        self.servers = self.spec.get("servers", [])
        self.paths = self.spec.get("paths", {})
        self.components = self.spec.get("components", {})
    
    def generate_python_sdk(self) -> str:
        """Generate Python SDK"""
        sdk_content = f'''"""
{self.info.get("title", "API")} Python SDK
Version: {self.info.get("version", "1.0.0")}
Generated: {datetime.now().isoformat()}

{self.info.get("description", "")}
"""

from typing import Dict, Any, Optional, List
import requests
from datetime import datetime
import json
from urllib.parse import urljoin


class RoadtripStorytellerError(Exception):
    """Base exception for SDK errors"""
    def __init__(self, message: str, status_code: int = None, response: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class AuthenticationError(RoadtripStorytellerError):
    """Authentication failed"""
    pass


class RateLimitError(RoadtripStorytellerError):
    """Rate limit exceeded"""
    pass


class ValidationError(RoadtripStorytellerError):
    """Request validation failed"""
    pass


class RoadtripStorytellerClient:
    """
    AI Road Trip Storyteller API Client
    
    Example:
        client = RoadtripStorytellerClient(api_key="your-api-key")
        story = client.stories.generate(
            latitude=40.7128,
            longitude=-74.0060,
            story_type="historical"
        )
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        base_url: str = "{self.servers[0].get('url', 'https://api.roadtripstoryteller.com')}",
        timeout: int = 30,
        retry_count: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout
        self.retry_count = retry_count
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({{
            'Content-Type': 'application/json',
            'User-Agent': 'RoadtripStoryteller-Python-SDK/1.0.0'
        }})
        
        # Set authentication
        if access_token:
            self.session.headers['Authorization'] = f'Bearer {{access_token}}'
        elif api_key:
            self.session.headers['X-API-Key'] = api_key
        
        # Initialize service modules
        self.auth = AuthService(self)
        self.stories = StoryService(self)
        self.voice = VoiceService(self)
        self.bookings = BookingService(self)
        self.trips = TripService(self)
        self.users = UserService(self)
    
    def set_access_token(self, token: str):
        """Update access token"""
        self.access_token = token
        self.session.headers['Authorization'] = f'Bearer {{token}}'
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    files=files,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RateLimitError(
                        f"Rate limit exceeded. Retry after {{retry_after}} seconds",
                        status_code=429,
                        response=response.json() if response.text else None
                    )
                
                # Handle authentication errors
                if response.status_code == 401:
                    raise AuthenticationError(
                        "Authentication failed",
                        status_code=401,
                        response=response.json() if response.text else None
                    )
                
                # Handle validation errors
                if response.status_code == 422:
                    raise ValidationError(
                        "Validation error",
                        status_code=422,
                        response=response.json() if response.text else None
                    )
                
                # Handle other errors
                response.raise_for_status()
                
                # Return JSON response
                return response.json() if response.text else {{}}
                
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_count - 1:
                    raise RoadtripStorytellerError(f"Request failed: {{str(e)}}")
                continue


class AuthService:
    """Authentication service"""
    
    def __init__(self, client: RoadtripStorytellerClient):
        self.client = client
    
    def register(self, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user"""
        return self.client._request(
            'POST',
            '/api/auth/register',
            json_data={{
                'email': email,
                'password': password,
                'full_name': full_name
            }}
        )
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login and get access token"""
        response = self.client._request(
            'POST',
            '/api/auth/login',
            json_data={{
                'email': email,
                'password': password
            }}
        )
        
        # Automatically set the access token
        if 'access_token' in response:
            self.client.set_access_token(response['access_token'])
        
        return response
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        response = self.client._request(
            'POST',
            '/api/auth/refresh',
            json_data={{'refresh_token': refresh_token}}
        )
        
        # Update access token
        if 'access_token' in response:
            self.client.set_access_token(response['access_token'])
        
        return response
    
    def logout(self) -> Dict[str, Any]:
        """Logout current session"""
        return self.client._request('POST', '/api/auth/logout')


class StoryService:
    """Story generation and management"""
    
    def __init__(self, client: RoadtripStorytellerClient):
        self.client = client
    
    def generate(
        self,
        latitude: float,
        longitude: float,
        story_type: str = "auto",
        personality: str = "morgan_freeman",
        include_local_facts: bool = True,
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate AI story for location"""
        return self.client._request(
            'POST',
            '/api/story/generate',
            json_data={{
                'latitude': latitude,
                'longitude': longitude,
                'story_type': story_type,
                'personality': personality,
                'include_local_facts': include_local_facts,
                'language': language,
                **kwargs
            }}
        )
    
    def get_story(self, story_id: str) -> Dict[str, Any]:
        """Get story by ID"""
        return self.client._request('GET', f'/api/story/{{story_id}}')
    
    def list_stories(
        self,
        page: int = 1,
        per_page: int = 10,
        trip_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List user's stories"""
        return self.client._request(
            'GET',
            '/api/stories',
            params={{
                'page': page,
                'per_page': per_page,
                'trip_id': trip_id
            }}
        )


class VoiceService:
    """Voice interaction service"""
    
    def __init__(self, client: RoadtripStorytellerClient):
        self.client = client
    
    def process_command(self, audio_file: Any, language: str = "en-US") -> Dict[str, Any]:
        """Process voice command"""
        return self.client._request(
            'POST',
            '/api/voice/command',
            files={{'audio': audio_file}},
            data={{'language': language}}
        )
    
    def text_to_speech(
        self,
        text: str,
        voice: str = "morgan_freeman",
        language: str = "en-US",
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """Convert text to speech"""
        return self.client._request(
            'POST',
            '/api/tts/generate',
            json_data={{
                'text': text,
                'voice': voice,
                'language': language,
                'speed': speed
            }}
        )
    
    def list_personalities(self) -> Dict[str, Any]:
        """List available voice personalities"""
        return self.client._request('GET', '/api/voice/personalities')


class BookingService:
    """Booking and reservation service"""
    
    def __init__(self, client: RoadtripStorytellerClient):
        self.client = client
    
    def search_hotels(
        self,
        latitude: float,
        longitude: float,
        checkin: str,
        checkout: str,
        radius: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for hotels"""
        return self.client._request(
            'GET',
            '/api/bookings/hotels/search',
            params={{
                'latitude': latitude,
                'longitude': longitude,
                'checkin': checkin,
                'checkout': checkout,
                'radius': radius,
                **kwargs
            }}
        )
    
    def book_hotel(self, hotel_id: str, checkin: str, checkout: str, **kwargs) -> Dict[str, Any]:
        """Book a hotel"""
        return self.client._request(
            'POST',
            '/api/bookings/hotels/book',
            json_data={{
                'hotel_id': hotel_id,
                'checkin': checkin,
                'checkout': checkout,
                **kwargs
            }}
        )
    
    def search_restaurants(
        self,
        latitude: float,
        longitude: float,
        cuisine: Optional[str] = None,
        price_range: Optional[str] = None,
        radius: int = 5
    ) -> Dict[str, Any]:
        """Search for restaurants"""
        return self.client._request(
            'GET',
            '/api/bookings/restaurants/search',
            params={{
                'latitude': latitude,
                'longitude': longitude,
                'cuisine': cuisine,
                'price_range': price_range,
                'radius': radius
            }}
        )


class TripService:
    """Trip planning and management"""
    
    def __init__(self, client: RoadtripStorytellerClient):
        self.client = client
    
    def create_trip(
        self,
        name: str,
        start_location: Dict[str, Any],
        end_location: Dict[str, Any],
        start_date: str,
        waypoints: Optional[List[Dict[str, Any]]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new trip"""
        return self.client._request(
            'POST',
            '/api/trips/create',
            json_data={{
                'name': name,
                'start_location': start_location,
                'end_location': end_location,
                'start_date': start_date,
                'waypoints': waypoints or [],
                'preferences': preferences or {{}}
            }}
        )
    
    def get_trip(self, trip_id: str) -> Dict[str, Any]:
        """Get trip details"""
        return self.client._request('GET', f'/api/trips/{{trip_id}}')
    
    def update_trip(self, trip_id: str, **updates) -> Dict[str, Any]:
        """Update trip details"""
        return self.client._request('PATCH', f'/api/trips/{{trip_id}}', json_data=updates)
    
    def start_trip(self, trip_id: str) -> Dict[str, Any]:
        """Start a trip"""
        return self.client._request('POST', f'/api/trips/{{trip_id}}/start')
    
    def end_trip(self, trip_id: str) -> Dict[str, Any]:
        """End a trip"""
        return self.client._request('POST', f'/api/trips/{{trip_id}}/end')


class UserService:
    """User profile and preferences"""
    
    def __init__(self, client: RoadtripStorytellerClient):
        self.client = client
    
    def get_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        return self.client._request('GET', '/api/users/profile')
    
    def update_profile(self, **updates) -> Dict[str, Any]:
        """Update user profile"""
        return self.client._request('PATCH', '/api/users/profile', json_data=updates)
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user preferences"""
        return self.client._request('GET', '/api/users/preferences')
    
    def update_preferences(self, **preferences) -> Dict[str, Any]:
        """Update user preferences"""
        return self.client._request('PUT', '/api/users/preferences', json_data=preferences)
'''
        
        return sdk_content
    
    def generate_javascript_sdk(self) -> str:
        """Generate JavaScript/TypeScript SDK"""
        sdk_content = f'''/**
 * {self.info.get("title", "API")} JavaScript SDK
 * Version: {self.info.get("version", "1.0.0")}
 * Generated: {datetime.now().isoformat()}
 * 
 * {self.info.get("description", "")}
 */

export interface Config {{
  apiKey?: string;
  accessToken?: string;
  baseUrl?: string;
  timeout?: number;
  retryCount?: number;
}}

export interface Location {{
  latitude: number;
  longitude: number;
  name?: string;
  address?: string;
}}

export interface StoryGenerateParams {{
  latitude: number;
  longitude: number;
  storyType?: string;
  personality?: string;
  includeLocalFacts?: boolean;
  language?: string;
}}

export interface TripCreateParams {{
  name: string;
  startLocation: Location;
  endLocation: Location;
  startDate: string;
  waypoints?: Location[];
  preferences?: Record<string, any>;
}}

export class RoadtripStorytellerError extends Error {{
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {{
    super(message);
    this.name = 'RoadtripStorytellerError';
  }}
}}

export class AuthenticationError extends RoadtripStorytellerError {{
  constructor(message: string, statusCode?: number, response?: any) {{
    super(message, statusCode, response);
    this.name = 'AuthenticationError';
  }}
}}

export class RateLimitError extends RoadtripStorytellerError {{
  constructor(message: string, statusCode?: number, response?: any) {{
    super(message, statusCode, response);
    this.name = 'RateLimitError';
  }}
}}

export class ValidationError extends RoadtripStorytellerError {{
  constructor(message: string, statusCode?: number, response?: any) {{
    super(message, statusCode, response);
    this.name = 'ValidationError';
  }}
}}

export class RoadtripStorytellerClient {{
  private config: Config;
  private baseUrl: string;
  private headers: Record<string, string>;
  
  public auth: AuthService;
  public stories: StoryService;
  public voice: VoiceService;
  public bookings: BookingService;
  public trips: TripService;
  public users: UserService;
  
  constructor(config: Config = {{}}) {{
    this.config = {{
      baseUrl: '{self.servers[0].get('url', 'https://api.roadtripstoryteller.com')}',
      timeout: 30000,
      retryCount: 3,
      ...config
    }};
    
    this.baseUrl = this.config.baseUrl!.replace(/\/$/, '');
    this.headers = {{
      'Content-Type': 'application/json',
      'User-Agent': 'RoadtripStoryteller-JS-SDK/1.0.0'
    }};
    
    // Set authentication
    if (this.config.accessToken) {{
      this.headers['Authorization'] = `Bearer ${{this.config.accessToken}}`;
    }} else if (this.config.apiKey) {{
      this.headers['X-API-Key'] = this.config.apiKey;
    }}
    
    // Initialize services
    this.auth = new AuthService(this);
    this.stories = new StoryService(this);
    this.voice = new VoiceService(this);
    this.bookings = new BookingService(this);
    this.trips = new TripService(this);
    this.users = new UserService(this);
  }}
  
  setAccessToken(token: string): void {{
    this.config.accessToken = token;
    this.headers['Authorization'] = `Bearer ${{token}}`;
  }}
  
  async request<T = any>(
    method: string,
    endpoint: string,
    options: {{
      params?: Record<string, any>;
      body?: any;
      headers?: Record<string, string>;
    }} = {{}}
  ): Promise<T> {{
    const url = new URL(`${{this.baseUrl}}${{endpoint}}`);
    
    // Add query parameters
    if (options.params) {{
      Object.entries(options.params).forEach(([key, value]) => {{
        if (value !== undefined && value !== null) {{
          url.searchParams.append(key, String(value));
        }}
      }});
    }}
    
    const fetchOptions: RequestInit = {{
      method,
      headers: {{ ...this.headers, ...options.headers }},
      signal: AbortSignal.timeout(this.config.timeout!)
    }};
    
    if (options.body && method !== 'GET') {{
      fetchOptions.body = JSON.stringify(options.body);
    }}
    
    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt < this.config.retryCount!; attempt++) {{
      try {{
        const response = await fetch(url.toString(), fetchOptions);
        
        if (response.status === 429) {{
          const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
          throw new RateLimitError(
            `Rate limit exceeded. Retry after ${{retryAfter}} seconds`,
            429,
            await response.json().catch(() => null)
          );
        }}
        
        if (response.status === 401) {{
          throw new AuthenticationError(
            'Authentication failed',
            401,
            await response.json().catch(() => null)
          );
        }}
        
        if (response.status === 422) {{
          throw new ValidationError(
            'Validation error',
            422,
            await response.json().catch(() => null)
          );
        }}
        
        if (!response.ok) {{
          throw new RoadtripStorytellerError(
            `Request failed with status ${{response.status}}`,
            response.status,
            await response.json().catch(() => null)
          );
        }}
        
        return await response.json();
      }} catch (error) {{
        lastError = error as Error;
        if (attempt === this.config.retryCount! - 1) {{
          throw lastError;
        }}
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
      }}
    }}
    
    throw lastError!;
  }}
}}

export class AuthService {{
  constructor(private client: RoadtripStorytellerClient) {{}}
  
  async register(email: string, password: string, fullName?: string): Promise<any> {{
    return this.client.request('POST', '/api/auth/register', {{
      body: {{ email, password, full_name: fullName }}
    }});
  }}
  
  async login(email: string, password: string): Promise<any> {{
    const response = await this.client.request('POST', '/api/auth/login', {{
      body: {{ email, password }}
    }});
    
    if (response.access_token) {{
      this.client.setAccessToken(response.access_token);
    }}
    
    return response;
  }}
  
  async refreshToken(refreshToken: string): Promise<any> {{
    const response = await this.client.request('POST', '/api/auth/refresh', {{
      body: {{ refresh_token: refreshToken }}
    }});
    
    if (response.access_token) {{
      this.client.setAccessToken(response.access_token);
    }}
    
    return response;
  }}
  
  async logout(): Promise<any> {{
    return this.client.request('POST', '/api/auth/logout');
  }}
}}

export class StoryService {{
  constructor(private client: RoadtripStorytellerClient) {{}}
  
  async generate(params: StoryGenerateParams): Promise<any> {{
    return this.client.request('POST', '/api/story/generate', {{
      body: {{
        latitude: params.latitude,
        longitude: params.longitude,
        story_type: params.storyType,
        personality: params.personality,
        include_local_facts: params.includeLocalFacts,
        language: params.language
      }}
    }});
  }}
  
  async getStory(storyId: string): Promise<any> {{
    return this.client.request('GET', `/api/story/${{storyId}}`);
  }}
  
  async listStories(page = 1, perPage = 10, tripId?: string): Promise<any> {{
    return this.client.request('GET', '/api/stories', {{
      params: {{ page, per_page: perPage, trip_id: tripId }}
    }});
  }}
}}

export class VoiceService {{
  constructor(private client: RoadtripStorytellerClient) {{}}
  
  async processCommand(audioFile: File | Blob, language = 'en-US'): Promise<any> {{
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('language', language);
    
    return this.client.request('POST', '/api/voice/command', {{
      body: formData,
      headers: {{ 'Content-Type': undefined }} // Let browser set content type
    }});
  }}
  
  async textToSpeech(
    text: string,
    voice = 'morgan_freeman',
    language = 'en-US',
    speed = 1.0
  ): Promise<any> {{
    return this.client.request('POST', '/api/tts/generate', {{
      body: {{ text, voice, language, speed }}
    }});
  }}
  
  async listPersonalities(): Promise<any> {{
    return this.client.request('GET', '/api/voice/personalities');
  }}
}}

export class BookingService {{
  constructor(private client: RoadtripStorytellerClient) {{}}
  
  async searchHotels(
    latitude: number,
    longitude: number,
    checkin: string,
    checkout: string,
    radius = 10
  ): Promise<any> {{
    return this.client.request('GET', '/api/bookings/hotels/search', {{
      params: {{ latitude, longitude, checkin, checkout, radius }}
    }});
  }}
  
  async bookHotel(hotelId: string, checkin: string, checkout: string): Promise<any> {{
    return this.client.request('POST', '/api/bookings/hotels/book', {{
      body: {{ hotel_id: hotelId, checkin, checkout }}
    }});
  }}
  
  async searchRestaurants(
    latitude: number,
    longitude: number,
    cuisine?: string,
    priceRange?: string,
    radius = 5
  ): Promise<any> {{
    return this.client.request('GET', '/api/bookings/restaurants/search', {{
      params: {{
        latitude,
        longitude,
        cuisine,
        price_range: priceRange,
        radius
      }}
    }});
  }}
}}

export class TripService {{
  constructor(private client: RoadtripStorytellerClient) {{}}
  
  async createTrip(params: TripCreateParams): Promise<any> {{
    return this.client.request('POST', '/api/trips/create', {{
      body: {{
        name: params.name,
        start_location: params.startLocation,
        end_location: params.endLocation,
        start_date: params.startDate,
        waypoints: params.waypoints,
        preferences: params.preferences
      }}
    }});
  }}
  
  async getTrip(tripId: string): Promise<any> {{
    return this.client.request('GET', `/api/trips/${{tripId}}`);
  }}
  
  async updateTrip(tripId: string, updates: Record<string, any>): Promise<any> {{
    return this.client.request('PATCH', `/api/trips/${{tripId}}`, {{
      body: updates
    }});
  }}
  
  async startTrip(tripId: string): Promise<any> {{
    return this.client.request('POST', `/api/trips/${{tripId}}/start`);
  }}
  
  async endTrip(tripId: string): Promise<any> {{
    return this.client.request('POST', `/api/trips/${{tripId}}/end`);
  }}
}}

export class UserService {{
  constructor(private client: RoadtripStorytellerClient) {{}}
  
  async getProfile(): Promise<any> {{
    return this.client.request('GET', '/api/users/profile');
  }}
  
  async updateProfile(updates: Record<string, any>): Promise<any> {{
    return this.client.request('PATCH', '/api/users/profile', {{
      body: updates
    }});
  }}
  
  async getPreferences(): Promise<any> {{
    return this.client.request('GET', '/api/users/preferences');
  }}
  
  async updatePreferences(preferences: Record<string, any>): Promise<any> {{
    return this.client.request('PUT', '/api/users/preferences', {{
      body: preferences
    }});
  }}
}}

// Export default client
export default RoadtripStorytellerClient;
'''
        
        return sdk_content
    
    def generate_react_native_sdk(self) -> str:
        """Generate React Native SDK"""
        sdk_content = f'''/**
 * {self.info.get("title", "API")} React Native SDK
 * Version: {self.info.get("version", "1.0.0")}
 * Generated: {datetime.now().isoformat()}
 * 
 * {self.info.get("description", "")}
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import * as Audio from 'expo-av';
import * as FileSystem from 'expo-file-system';

export interface Config {{
  apiKey?: string;
  accessToken?: string;
  baseUrl?: string;
  timeout?: number;
  retryCount?: number;
  persistAuth?: boolean;
}}

export interface DeviceLocation {{
  latitude: number;
  longitude: number;
  accuracy?: number;
  altitude?: number;
  speed?: number;
  heading?: number;
}}

const AUTH_STORAGE_KEY = '@roadtrip_auth';

export class RoadtripStorytellerMobileClient {{
  private config: Config;
  private baseUrl: string;
  private headers: Record<string, string>;
  private locationSubscription: Location.LocationSubscription | null = null;
  private audioPlayer: Audio.Sound | null = null;
  
  public auth: MobileAuthService;
  public stories: MobileStoryService;
  public voice: MobileVoiceService;
  public location: LocationService;
  public audio: AudioService;
  
  constructor(config: Config = {{}}) {{
    this.config = {{
      baseUrl: '{self.servers[0].get('url', 'https://api.roadtripstoryteller.com')}',
      timeout: 30000,
      retryCount: 3,
      persistAuth: true,
      ...config
    }};
    
    this.baseUrl = this.config.baseUrl!.replace(/\/$/, '');
    this.headers = {{
      'Content-Type': 'application/json',
      'User-Agent': 'RoadtripStoryteller-ReactNative-SDK/1.0.0'
    }};
    
    // Initialize services
    this.auth = new MobileAuthService(this);
    this.stories = new MobileStoryService(this);
    this.voice = new MobileVoiceService(this);
    this.location = new LocationService(this);
    this.audio = new AudioService(this);
    
    // Load persisted auth
    this.loadPersistedAuth();
  }}
  
  private async loadPersistedAuth(): Promise<void> {{
    if (!this.config.persistAuth) return;
    
    try {{
      const authData = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
      if (authData) {{
        const {{ accessToken }} = JSON.parse(authData);
        if (accessToken) {{
          this.setAccessToken(accessToken);
        }}
      }}
    }} catch (error) {{
      console.error('Failed to load persisted auth:', error);
    }}
  }}
  
  async setAccessToken(token: string): Promise<void> {{
    this.config.accessToken = token;
    this.headers['Authorization'] = `Bearer ${{token}}`;
    
    if (this.config.persistAuth) {{
      try {{
        await AsyncStorage.setItem(
          AUTH_STORAGE_KEY,
          JSON.stringify({{ accessToken: token }})
        );
      }} catch (error) {{
        console.error('Failed to persist auth:', error);
      }}
    }}
  }}
  
  async clearAuth(): Promise<void> {{
    delete this.config.accessToken;
    delete this.headers['Authorization'];
    
    if (this.config.persistAuth) {{
      try {{
        await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
      }} catch (error) {{
        console.error('Failed to clear persisted auth:', error);
      }}
    }}
  }}
  
  async request<T = any>(
    method: string,
    endpoint: string,
    options: {{
      params?: Record<string, any>;
      body?: any;
      headers?: Record<string, string>;
    }} = {{}}
  ): Promise<T> {{
    const url = new URL(`${{this.baseUrl}}${{endpoint}}`);
    
    // Add query parameters
    if (options.params) {{
      Object.entries(options.params).forEach(([key, value]) => {{
        if (value !== undefined && value !== null) {{
          url.searchParams.append(key, String(value));
        }}
      }});
    }}
    
    const fetchOptions: RequestInit = {{
      method,
      headers: {{ ...this.headers, ...options.headers }},
    }};
    
    if (options.body && method !== 'GET') {{
      fetchOptions.body = JSON.stringify(options.body);
    }}
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout!);
    
    try {{
      const response = await fetch(url.toString(), {{
        ...fetchOptions,
        signal: controller.signal
      }});
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {{
        const errorData = await response.json().catch(() => ({{}}));
        throw new Error(`Request failed: ${{response.status}} - ${{errorData.detail || response.statusText}}`);
      }}
      
      return await response.json();
    }} catch (error) {{
      clearTimeout(timeoutId);
      throw error;
    }}
  }}
}}

export class MobileAuthService {{
  constructor(private client: RoadtripStorytellerMobileClient) {{}}
  
  async login(email: string, password: string): Promise<any> {{
    const response = await this.client.request('POST', '/api/auth/login', {{
      body: {{ email, password }}
    }});
    
    if (response.access_token) {{
      await this.client.setAccessToken(response.access_token);
    }}
    
    return response;
  }}
  
  async logout(): Promise<void> {{
    await this.client.request('POST', '/api/auth/logout');
    await this.client.clearAuth();
  }}
}}

export class MobileStoryService {{
  constructor(private client: RoadtripStorytellerMobileClient) {{}}
  
  async generateForCurrentLocation(
    storyType = 'auto',
    personality = 'morgan_freeman'
  ): Promise<any> {{
    const location = await this.client.location.getCurrentLocation();
    
    return this.client.request('POST', '/api/story/generate', {{
      body: {{
        latitude: location.latitude,
        longitude: location.longitude,
        story_type: storyType,
        personality: personality,
        include_local_facts: true,
        device_info: {{
          accuracy: location.accuracy,
          speed: location.speed,
          heading: location.heading
        }}
      }}
    }});
  }}
}}

export class MobileVoiceService {{
  constructor(private client: RoadtripStorytellerMobileClient) {{}}
  
  async startListening(): Promise<void> {{
    const {{ status }} = await Audio.requestPermissionsAsync();
    if (status !== 'granted') {{
      throw new Error('Audio permissions not granted');
    }}
    
    await Audio.setAudioModeAsync({{
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    }});
  }}
  
  async processVoiceCommand(audioUri: string): Promise<any> {{
    const fileInfo = await FileSystem.getInfoAsync(audioUri);
    if (!fileInfo.exists) {{
      throw new Error('Audio file not found');
    }}
    
    const formData = new FormData();
    formData.append('audio', {{
      uri: audioUri,
      type: 'audio/wav',
      name: 'voice_command.wav'
    }} as any);
    
    return this.client.request('POST', '/api/voice/command', {{
      body: formData,
      headers: {{ 'Content-Type': 'multipart/form-data' }}
    }});
  }}
}}

export class LocationService {{
  private watchSubscription: Location.LocationSubscription | null = null;
  
  constructor(private client: RoadtripStorytellerMobileClient) {{}}
  
  async getCurrentLocation(): Promise<DeviceLocation> {{
    const {{ status }} = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {{
      throw new Error('Location permissions not granted');
    }}
    
    const location = await Location.getCurrentPositionAsync({{
      accuracy: Location.Accuracy.High
    }});
    
    return {{
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
      accuracy: location.coords.accuracy || undefined,
      altitude: location.coords.altitude || undefined,
      speed: location.coords.speed || undefined,
      heading: location.coords.heading || undefined
    }};
  }}
  
  async startLocationTracking(callback: (location: DeviceLocation) => void): Promise<void> {{
    const {{ status }} = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {{
      throw new Error('Location permissions not granted');
    }}
    
    this.watchSubscription = await Location.watchPositionAsync(
      {{
        accuracy: Location.Accuracy.High,
        timeInterval: 5000,
        distanceInterval: 10
      }},
      (location) => {{
        callback({{
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          accuracy: location.coords.accuracy || undefined,
          altitude: location.coords.altitude || undefined,
          speed: location.coords.speed || undefined,
          heading: location.coords.heading || undefined
        }});
      }}
    );
  }}
  
  stopLocationTracking(): void {{
    if (this.watchSubscription) {{
      this.watchSubscription.remove();
      this.watchSubscription = null;
    }}
  }}
}}

export class AudioService {{
  private currentSound: Audio.Sound | null = null;
  
  constructor(private client: RoadtripStorytellerMobileClient) {{}}
  
  async playStoryAudio(audioUrl: string): Promise<void> {{
    try {{
      // Stop current audio if playing
      await this.stopAudio();
      
      // Configure audio mode
      await Audio.setAudioModeAsync({{
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: true,
      }});
      
      // Load and play audio
      const {{ sound }} = await Audio.Sound.createAsync(
        {{ uri: audioUrl }},
        {{ shouldPlay: true }}
      );
      
      this.currentSound = sound;
      
      // Set up playback status updates
      sound.setOnPlaybackStatusUpdate((status) => {{
        if (status.isLoaded && status.didJustFinish) {{
          this.currentSound = null;
        }}
      }});
    }} catch (error) {{
      console.error('Failed to play audio:', error);
      throw error;
    }}
  }}
  
  async pauseAudio(): Promise<void> {{
    if (this.currentSound) {{
      await this.currentSound.pauseAsync();
    }}
  }}
  
  async resumeAudio(): Promise<void> {{
    if (this.currentSound) {{
      await this.currentSound.playAsync();
    }}
  }}
  
  async stopAudio(): Promise<void> {{
    if (this.currentSound) {{
      await this.currentSound.stopAsync();
      await this.currentSound.unloadAsync();
      this.currentSound = null;
    }}
  }}
  
  async getPlaybackStatus(): Promise<Audio.AVPlaybackStatus | null> {{
    if (this.currentSound) {{
      return await this.currentSound.getStatusAsync();
    }}
    return null;
  }}
}}

// Export default client
export default RoadtripStorytellerMobileClient;
'''
        
        return sdk_content
    
    def generate_postman_collection(self) -> Dict[str, Any]:
        """Generate Postman collection from OpenAPI spec"""
        collection = {
            "info": {
                "name": self.info.get("title", "API Collection"),
                "description": self.info.get("description", ""),
                "version": self.info.get("version", "1.0.0"),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{access_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": self.servers[0].get("url", "https://api.example.com") if self.servers else "https://api.example.com",
                    "type": "string"
                },
                {
                    "key": "access_token",
                    "value": "",
                    "type": "string",
                    "description": "JWT access token from login endpoint"
                }
            ],
            "item": []
        }
        
        # Group endpoints by tags
        tag_groups = {}
        
        for path, methods in self.paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    tags = operation.get("tags", ["Default"])
                    tag = tags[0] if tags else "Default"
                    
                    if tag not in tag_groups:
                        tag_groups[tag] = {
                            "name": tag,
                            "item": [],
                            "description": f"Endpoints for {tag}"
                        }
                    
                    # Create request item
                    request_item = self._create_postman_request(
                        method, path, operation
                    )
                    tag_groups[tag]["item"].append(request_item)
        
        # Add folders to collection
        collection["item"] = list(tag_groups.values())
        
        # Add example environment
        collection["event"] = [
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "// Pre-request script",
                        "// Add any global pre-request logic here"
                    ]
                }
            },
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "// Global test script",
                        "// Save access token from login response",
                        "if (pm.response.json().access_token) {",
                        "    pm.collectionVariables.set('access_token', pm.response.json().access_token);",
                        "}"
                    ]
                }
            }
        ]
        
        return collection
    
    def _create_postman_request(self, method: str, path: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Postman request item"""
        # Replace path parameters with Postman variables
        postman_path = path
        if "{" in path:
            import re
            postman_path = re.sub(r'\{(\w+)\}', r':{$1}', path)
        
        request = {
            "name": operation.get("summary", f"{method.upper()} {path}"),
            "request": {
                "method": method.upper(),
                "header": [],
                "url": {
                    "raw": f"{{{{base_url}}}}{postman_path}",
                    "host": ["{{base_url}}"],
                    "path": postman_path.strip("/").split("/")
                }
            }
        }
        
        # Add description
        if "description" in operation:
            request["request"]["description"] = operation["description"]
        
        # Add query parameters
        if "parameters" in operation:
            query_params = []
            path_variables = []
            
            for param in operation["parameters"]:
                if param.get("in") == "query":
                    query_params.append({
                        "key": param["name"],
                        "value": "",
                        "description": param.get("description", ""),
                        "disabled": not param.get("required", False)
                    })
                elif param.get("in") == "path":
                    path_variables.append({
                        "key": param["name"],
                        "value": "",
                        "description": param.get("description", "")
                    })
            
            if query_params:
                request["request"]["url"]["query"] = query_params
            if path_variables:
                request["request"]["url"]["variable"] = path_variables
        
        # Add request body
        if "requestBody" in operation:
            content = operation["requestBody"].get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                example = content["application/json"].get("example", {})
                
                request["request"]["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(example, indent=2) if example else "{}",
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }
                request["request"]["header"].append({
                    "key": "Content-Type",
                    "value": "application/json"
                })
        
        # Add example responses
        if "responses" in operation:
            examples = []
            for status_code, response in operation["responses"].items():
                example_response = {
                    "name": f"{status_code} - {response.get('description', 'Response')}",
                    "originalRequest": request["request"].copy(),
                    "status": response.get("description", ""),
                    "code": int(status_code) if status_code.isdigit() else 200,
                    "_postman_previewlanguage": "json",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ]
                }
                
                # Add response body example
                if "content" in response and "application/json" in response["content"]:
                    content = response["content"]["application/json"]
                    if "example" in content:
                        example_response["body"] = json.dumps(content["example"], indent=2)
                
                examples.append(example_response)
            
            if examples:
                request["response"] = examples
        
        return request


def generate_sdks_from_openapi(openapi_spec: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    """Generate SDKs in multiple languages from OpenAPI spec"""
    generator = SDKGenerator(openapi_spec)
    output_paths = {}
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate Python SDK
    python_sdk = generator.generate_python_sdk()
    python_path = output_dir / "python" / "roadtrip_storyteller.py"
    python_path.parent.mkdir(exist_ok=True)
    python_path.write_text(python_sdk)
    output_paths["python"] = python_path
    
    # Generate JavaScript SDK
    js_sdk = generator.generate_javascript_sdk()
    js_path = output_dir / "javascript" / "roadtrip-storyteller.js"
    js_path.parent.mkdir(exist_ok=True)
    js_path.write_text(js_sdk)
    output_paths["javascript"] = js_path
    
    # Generate TypeScript definitions
    ts_path = output_dir / "javascript" / "roadtrip-storyteller.d.ts"
    ts_path.write_text(js_sdk)  # The JS SDK is already in TypeScript
    output_paths["typescript"] = ts_path
    
    # Generate React Native SDK
    rn_sdk = generator.generate_react_native_sdk()
    rn_path = output_dir / "react-native" / "roadtrip-storyteller-mobile.js"
    rn_path.parent.mkdir(exist_ok=True)
    rn_path.write_text(rn_sdk)
    output_paths["react-native"] = rn_path
    
    # Generate Postman collection
    postman_collection = generator.generate_postman_collection()
    postman_path = output_dir / "postman" / "roadtrip-storyteller.postman_collection.json"
    postman_path.parent.mkdir(exist_ok=True)
    postman_path.write_text(json.dumps(postman_collection, indent=2))
    output_paths["postman"] = postman_path
    
    # Generate README for SDKs
    readme_content = f"""# AI Road Trip Storyteller SDKs

Generated from OpenAPI specification v{openapi_spec.get('info', {}).get('version', '1.0.0')}

## Available SDKs

### Python SDK
Located in: `python/roadtrip_storyteller.py`

Installation:
```bash
pip install roadtrip-storyteller
```

Usage:
```python
from roadtrip_storyteller import RoadtripStorytellerClient

client = RoadtripStorytellerClient(access_token="your-token")
story = client.stories.generate(latitude=40.7128, longitude=-74.0060)
```

### JavaScript/TypeScript SDK
Located in: `javascript/roadtrip-storyteller.js`

Installation:
```bash
npm install @roadtrip/storyteller-sdk
```

Usage:
```javascript
import RoadtripStorytellerClient from '@roadtrip/storyteller-sdk';

const client = new RoadtripStorytellerClient({{ accessToken: 'your-token' }});
const story = await client.stories.generate({{
  latitude: 40.7128,
  longitude: -74.0060
}});
```

### React Native SDK
Located in: `react-native/roadtrip-storyteller-mobile.js`

Installation:
```bash
npm install @roadtrip/mobile-sdk
```

Additional dependencies:
```bash
expo install expo-location expo-av expo-file-system @react-native-async-storage/async-storage
```

Usage:
```javascript
import RoadtripStorytellerMobileClient from '@roadtrip/mobile-sdk';

const client = new RoadtripStorytellerMobileClient({{
  persistAuth: true
}});

// Login
await client.auth.login('user@example.com', 'password');

// Generate story for current location
const story = await client.stories.generateForCurrentLocation();

// Play story audio
await client.audio.playStoryAudio(story.audio_url);
```

### Postman Collection
Located in: `postman/roadtrip-storyteller.postman_collection.json`

Import into Postman and set the following variables:
- `base_url`: API base URL
- `access_token`: Your JWT token

## Authentication

All SDKs support multiple authentication methods:

1. **JWT Token** (recommended):
   ```
   Authorization: Bearer <token>
   ```

2. **API Key**:
   ```
   X-API-Key: <api-key>
   ```

## Error Handling

All SDKs include comprehensive error handling:

- `AuthenticationError`: Authentication failed
- `RateLimitError`: Rate limit exceeded
- `ValidationError`: Request validation failed
- `RoadtripStorytellerError`: General API errors

## Support

- Documentation: https://docs.roadtripstoryteller.com
- API Reference: https://api.roadtripstoryteller.com/docs
- Support: developers@roadtripstoryteller.com
"""
    
    readme_path = output_dir / "README.md"
    readme_path.write_text(readme_content)
    
    return output_paths