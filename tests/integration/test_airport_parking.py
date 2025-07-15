"""Integration tests for airport parking functionality."""

import pytest
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.parking_reservation import ParkingReservation
from backend.app.services.photo_storage_service import PhotoStorageService
from backend.app.services.return_journey_service import ReturnJourneyService


@pytest.fixture
def mock_storage_service():
    """Mock the photo storage service."""
    with patch('backend.app.routes.airport_parking.photo_storage_service') as mock:
        mock.upload_parking_photo.return_value = "https://storage.googleapis.com/test-bucket/parking/test-user/test-ref_20250527_123456.jpg"
        yield mock


@pytest.fixture
def mock_user(db: Session):
    """Create a test user."""
    user = User(
        id="test-user-123",
        email="test@example.com",
        username="testuser",
        hashed_password="hashed"
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def mock_parking_reservation(db: Session, mock_user):
    """Create a test parking reservation."""
    reservation = ParkingReservation(
        id="test-reservation-123",
        user_id=mock_user.id,
        type="parking",
        venue_name="LAX Airport",
        reservation_time=datetime.utcnow(),
        party_size="1 vehicle",
        status="confirmed",
        confirmation_number="TEST-BOOKING-123",
        parking_type="airport",
        location_name="LAX Airport",
        terminal="Terminal 4",
        lot_name="Lot C",
        check_in_time=datetime.utcnow(),
        check_out_time=datetime.utcnow() + timedelta(days=5),
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_color="Silver",
        license_plate="ABC123"
    )
    db.add(reservation)
    db.commit()
    return reservation


class TestAirportParkingRoutes:
    """Test airport parking functionality."""
    
    def test_upload_parking_photo(self, client: TestClient, mock_user, mock_parking_reservation, mock_storage_service, db: Session):
        """Test uploading a parking photo."""
        # Create mock file
        file_content = b"fake image content"
        files = {
            "photo": ("parking.jpg", io.BytesIO(file_content), "image/jpeg")
        }
        data = {
            "spot_number": "C-42",
            "lot_name": "Lot C",
            "terminal": "Terminal 4"
        }
        
        # Mock authentication
        with patch('backend.app.core.auth.get_current_user', return_value=mock_user):
            response = client.post(
                f"/api/airport-parking/reservations/{mock_parking_reservation.confirmation_number}/upload-photo",
                files=files,
                data=data
            )
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Photo uploaded successfully"
        assert "photo_url" in result
        assert result["booking_reference"] == mock_parking_reservation.confirmation_number
        
        # Verify storage service was called
        mock_storage_service.upload_parking_photo.assert_called_once()
        
        # Check database was updated
        db.refresh(mock_parking_reservation)
        assert mock_parking_reservation.parking_photo_url is not None
        assert mock_parking_reservation.spot_number == "C-42"
    
    def test_get_parking_details(self, client: TestClient, mock_user, mock_parking_reservation, db: Session):
        """Test retrieving parking details with photo."""
        # Add photo URL to reservation
        mock_parking_reservation.parking_photo_url = "https://example.com/photo.jpg"
        mock_parking_reservation.photo_uploaded_at = datetime.utcnow()
        db.commit()
        
        with patch('backend.app.core.auth.get_current_user', return_value=mock_user):
            response = client.get(
                f"/api/airport-parking/reservations/{mock_parking_reservation.confirmation_number}/parking-details"
            )
        
        assert response.status_code == 200
        result = response.json()
        assert result["booking_reference"] == mock_parking_reservation.confirmation_number
        assert result["location"] == "LAX Airport"
        assert result["vehicle"]["make"] == "Toyota"
        assert result["photo"]["url"] == "https://example.com/photo.jpg"
    
    def test_create_parking_reservation(self, client: TestClient, mock_user, db: Session):
        """Test creating a new parking reservation."""
        data = {
            "location_name": "SFO Airport",
            "parking_type": "airport",
            "check_in_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "check_out_time": (datetime.utcnow() + timedelta(days=4)).isoformat(),
            "vehicle_make": "Honda",
            "vehicle_model": "Accord",
            "vehicle_color": "Blue",
            "license_plate": "XYZ789",
            "terminal": "Terminal 2",
            "outbound_flight": "UA123",
            "return_flight": "UA456",
            "airline": "United Airlines"
        }
        
        # Mock booking service
        with patch('backend.app.routes.airport_parking.BookingService') as mock_booking_service:
            mock_booking = Mock()
            mock_booking.id = "new-booking-123"
            mock_booking.booking_reference = "NEW-REF-123"
            mock_booking_service.return_value.create_booking.return_value = mock_booking
            
            with patch('backend.app.core.auth.get_current_user', return_value=mock_user):
                response = client.post("/api/airport-parking/reservations", data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Parking reservation created successfully"
        assert result["booking_reference"] == "NEW-REF-123"
        assert result["location"] == "SFO Airport"
        assert "upload_photo_url" in result
    
    def test_get_upcoming_returns(self, client: TestClient, mock_user, mock_parking_reservation, db: Session):
        """Test getting upcoming parking returns."""
        # Set check-out time to be within 24 hours
        mock_parking_reservation.check_out_time = datetime.utcnow() + timedelta(hours=12)
        mock_parking_reservation.parking_photo_url = "https://example.com/photo.jpg"
        db.commit()
        
        with patch('backend.app.core.auth.get_current_user', return_value=mock_user):
            with patch('backend.app.services.return_journey_service.ReturnJourneyService.check_pending_returns') as mock_check:
                mock_check.return_value = [
                    {
                        "reservation_id": mock_parking_reservation.id,
                        "user_id": mock_user.id,
                        "location": "LAX Airport",
                        "check_out_time": mock_parking_reservation.check_out_time.isoformat(),
                        "parking_photo_url": mock_parking_reservation.parking_photo_url,
                        "spot_info": "Lot C - C-42"
                    }
                ]
                
                response = client.get("/api/airport-parking/upcoming-returns?hours_ahead=24")
        
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 1
        assert len(result["upcoming_returns"]) == 1
        assert result["upcoming_returns"][0]["location"] == "LAX Airport"
    
    def test_send_return_reminder(self, client: TestClient, mock_user, mock_parking_reservation, db: Session):
        """Test sending a return journey reminder."""
        # Add photo to reservation
        mock_parking_reservation.parking_photo_url = "https://example.com/photo.jpg"
        db.commit()
        
        with patch('backend.app.core.auth.get_current_user', return_value=mock_user):
            with patch('backend.app.services.return_journey_service.ReturnJourneyService.send_return_reminder') as mock_send:
                mock_send.return_value = True
                
                response = client.post(
                    f"/api/airport-parking/reservations/{mock_parking_reservation.confirmation_number}/send-reminder"
                )
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Return journey reminder sent successfully"
        assert result["parking_location"] == "LAX Airport"
    
    def test_invalid_photo_type(self, client: TestClient, mock_user, mock_parking_reservation):
        """Test uploading an invalid file type."""
        files = {
            "photo": ("document.pdf", io.BytesIO(b"fake pdf"), "application/pdf")
        }
        
        with patch('backend.app.core.auth.get_current_user', return_value=mock_user):
            response = client.post(
                f"/api/airport-parking/reservations/{mock_parking_reservation.confirmation_number}/upload-photo",
                files=files
            )
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestReturnJourneyService:
    """Test return journey automation service."""
    
    def test_schedule_return_journey(self, db: Session, mock_user, mock_parking_reservation):
        """Test scheduling a return journey."""
        service = ReturnJourneyService(db)
        
        # Mock directions service
        with patch.object(service.directions_service, 'get_directions') as mock_directions:
            mock_directions.return_value = {
                "routes": [{
                    "legs": [{
                        "duration": {"value": 1800}  # 30 minutes
                    }]
                }]
            }
            
            result = service.schedule_return_journey(
                parking_reservation_id=mock_parking_reservation.id,
                user_id=mock_user.id,
                buffer_minutes=30
            )
        
        assert result["scheduled"] is True
        assert result["travel_time_minutes"] == 30
        assert result["buffer_minutes"] == 30
        assert result["parking_location"] == "LAX Airport"
        
        # Check database was updated
        db.refresh(mock_parking_reservation)
        assert mock_parking_reservation.return_journey_scheduled is True
        assert mock_parking_reservation.estimated_pickup_time is not None
    
    def test_get_parking_photo_context(self, db: Session, mock_parking_reservation):
        """Test getting parking photo context."""
        mock_parking_reservation.parking_photo_url = "https://example.com/photo.jpg"
        mock_parking_reservation.photo_uploaded_at = datetime.utcnow()
        mock_parking_reservation.spot_number = "C-42"
        db.commit()
        
        service = ReturnJourneyService(db)
        
        with patch('backend.app.core.cache.cache_manager.get', return_value=None):
            with patch('backend.app.core.cache.cache_manager.set'):
                context = service.get_parking_photo_context(mock_parking_reservation.id)
        
        assert context is not None
        assert context["photo_url"] == "https://example.com/photo.jpg"
        assert context["location"] == "LAX Airport"
        assert context["spot"] == "C-42"
        assert context["vehicle"]["make"] == "Toyota"
        assert "walking_directions" in context


class TestPhotoStorageService:
    """Test photo storage service."""
    
    @patch('google.cloud.storage.Client')
    def test_upload_parking_photo(self, mock_storage_client):
        """Test uploading a photo to Google Cloud Storage."""
        # Mock bucket and blob
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.public_url = "https://storage.googleapis.com/test-bucket/parking/user123/ref123_20250527_123456.jpg"
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        
        # Create service with mocked client
        service = PhotoStorageService()
        service.storage_client = mock_storage_client.return_value
        service.bucket = mock_bucket
        
        # Test upload
        file_content = io.BytesIO(b"fake image content")
        url = service.upload_parking_photo(
            file=file_content,
            user_id="user123",
            booking_reference="ref123",
            file_extension="jpg"
        )
        
        assert url == mock_blob.public_url
        mock_blob.upload_from_file.assert_called_once()
        mock_blob.make_public.assert_called_once()
    
    @patch('google.cloud.storage.Client')
    def test_delete_photo(self, mock_storage_client):
        """Test deleting a photo from storage."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        
        service = PhotoStorageService()
        service.storage_client = mock_storage_client.return_value
        service.bucket = mock_bucket
        
        success = service.delete_photo("parking/user123/photo.jpg")
        
        assert success is True
        mock_blob.delete.assert_called_once()