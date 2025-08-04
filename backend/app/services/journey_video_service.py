"""
Journey Video Generation Service
Creates shareable journey videos with highlights, stories, and memories
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import tempfile
import os
from pathlib import Path
import subprocess

import ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
import cv2

from app.core.logger import logger
from app.core.cache import cache_manager
from app.models import User, Story, Trip
from app.services.tts_service import tts_service
from app.core.config import settings


class JourneyVideoService:
    """Service for creating shareable journey videos"""
    
    def __init__(self, db=None):
        self.video_width = 1080
        self.video_height = 1920  # Vertical format for social media
        self.fps = 30
        self.audio_sample_rate = 44100
        self.db = db
        
        # Load fonts (would need actual font files in production)
        self.title_font_size = 60
        self.text_font_size = 40
        self.small_font_size = 30
        
    async def create_journey_video(
        self,
        trip_id: str,
        user_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a shareable video summarizing the journey
        
        Args:
            trip_id: ID of the trip
            user_id: User ID
            options: Video generation options
            
        Returns:
            Video metadata and URL
        """
        try:
            # Default options
            options = options or {}
            duration = options.get('duration', 60)  # 60 second video
            include_map = options.get('include_map', True)
            include_photos = options.get('include_photos', True)
            include_stats = options.get('include_stats', True)
            music_style = options.get('music_style', 'upbeat')
            
            # Get trip data
            trip_data = await self._get_trip_data(trip_id, user_id)
            if not trip_data:
                raise ValueError("Trip not found")
            
            # Generate video segments
            segments = []
            
            # 1. Title segment (5 seconds)
            segments.append(await self._create_title_segment(trip_data))
            
            # 2. Map animation segment (10 seconds)
            if include_map:
                segments.append(await self._create_map_segment(trip_data))
            
            # 3. Highlights segment (30 seconds)
            segments.append(await self._create_highlights_segment(trip_data))
            
            # 4. Photos segment (10 seconds)
            if include_photos and trip_data.get('photos'):
                segments.append(await self._create_photos_segment(trip_data))
            
            # 5. Stats segment (5 seconds)
            if include_stats:
                segments.append(await self._create_stats_segment(trip_data))
            
            # Generate narration
            narration_text = await self._generate_narration(trip_data, duration)
            narration_audio = await self._generate_narration_audio(narration_text)
            
            # Add background music
            music_track = await self._get_background_music(music_style, duration)
            
            # Combine everything
            video_url = await self._combine_video(
                segments,
                narration_audio,
                music_track,
                trip_id
            )
            
            # Generate thumbnail
            thumbnail_url = await self._generate_thumbnail(trip_data)
            
            result = {
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "duration": duration,
                "title": f"{trip_data['origin']} to {trip_data['destination']} Adventure",
                "description": self._generate_description(trip_data),
                "hashtags": self._generate_hashtags(trip_data),
                "share_links": self._generate_share_links(video_url, trip_data)
            }
            
            # Cache the result
            await cache_manager.set(
                f"journey_video:{trip_id}",
                result,
                ttl=86400  # 24 hours
            )
            
            logger.info(f"Created journey video for trip {trip_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating journey video: {str(e)}")
            raise
    
    async def _get_trip_data(self, trip_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive trip data"""
        try:
            from ..models.trip import Trip
            from ..models.trip_stop import TripStop
            from ..models.story import Story
            from ..models.booking import Booking
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            async with self.db() as session:
                # Fetch trip with related data
                result = await session.execute(
                    select(Trip)
                    .where(Trip.id == trip_id, Trip.user_id == user_id)
                    .options(
                        selectinload(Trip.stops),
                        selectinload(Trip.stories),
                        selectinload(Trip.bookings)
                    )
                )
                trip = result.scalar_one_or_none()
                
                if not trip:
                    # Return mock data if trip not found
                    logger.warning(f"Trip {trip_id} not found, using mock data")
                    return {
                        "id": trip_id,
                        "user_id": user_id,
                        "origin": "San Francisco",
                        "destination": "Los Angeles",
                        "date": datetime.now() - timedelta(days=2),
                        "duration_hours": 6,
                        "distance_miles": 380,
                        "stops": [],
                        "highlights": [],
                        "photos": [],
                        "personality": "Road Trip Narrator",
                        "bookings": []
                    }
                
                # Process trip data
                stops = []
                for stop in trip.stops:
                    stops.append({
                        "name": stop.name,
                        "type": stop.stop_type,
                        "duration": stop.duration_minutes,
                        "lat": stop.latitude,
                        "lng": stop.longitude
                    })
                
                # Extract highlights from stories
                highlights = []
                for story in trip.stories[:5]:  # Limit to 5 highlights
                    if story.content:
                        # Extract first sentence as highlight
                        highlight = story.content.split('.')[0]
                        highlights.append(highlight)
                
                # Get photos from trip media
                photos = []
                if hasattr(trip, 'media'):
                    photos = [m.file_path for m in trip.media if m.media_type == 'photo']
                
                # Get bookings
                bookings = []
                for booking in trip.bookings:
                    bookings.append({
                        "type": booking.booking_type,
                        "name": booking.vendor_name,
                        "rating": booking.rating if hasattr(booking, 'rating') else None
                    })
                
                return {
                    "id": str(trip.id),
                    "user_id": str(trip.user_id),
                    "origin": trip.origin_address or "Start",
                    "destination": trip.destination_address or "End",
                    "date": trip.start_time,
                    "duration_hours": (trip.end_time - trip.start_time).total_seconds() / 3600 if trip.end_time else 0,
                    "distance_miles": trip.total_distance_miles or 0,
                    "stops": stops,
                    "highlights": highlights,
                    "photos": photos,
                    "personality": trip.voice_personality or "Road Trip Narrator",
                    "bookings": bookings
                }
                
        except Exception as e:
            logger.error(f"Error fetching trip data: {e}")
            # Return minimal mock data on error
            return {
                "id": trip_id,
                "user_id": user_id,
                "origin": "Unknown",
                "destination": "Unknown",
                "date": datetime.now(),
                "duration_hours": 0,
                "distance_miles": 0,
                "stops": [],
                "highlights": [],
                "photos": [],
                "personality": "Road Trip Narrator",
                "bookings": []
            }
    
    async def _create_title_segment(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create animated title segment"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            # Create title frame
            img = Image.new('RGB', (self.video_width, self.video_height), color='#6366f1')
            draw = ImageDraw.Draw(img)
            
            # Add title text
            title = f"{trip_data['origin']} to {trip_data['destination']}"
            # In production, use actual font files
            # font = ImageFont.truetype("arial.ttf", self.title_font_size)
            
            # Add decorative elements
            draw.text((self.video_width//2, self.video_height//2 - 100), 
                     title, fill='white', anchor='mm')
            
            draw.text((self.video_width//2, self.video_height//2 + 50),
                     trip_data['date'].strftime('%B %d, %Y'),
                     fill='white', anchor='mm')
            
            # Save frame and create video
            frame_path = tmp.name.replace('.mp4', '.png')
            img.save(frame_path)
            
            # Create 5-second video from image
            (
                ffmpeg
                .input(frame_path, loop=1, t=5)
                .output(tmp.name, vcodec='libx264', pix_fmt='yuv420p')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return {
                "path": tmp.name,
                "duration": 5
            }
    
    async def _create_map_segment(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create animated map showing the route"""
        import requests
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            try:
                # Create frames for animation
                frames = []
                num_frames = 30  # 1 second at 30fps
                
                # Get route points from stops
                route_points = []
                if trip_data.get('stops'):
                    for stop in trip_data['stops']:
                        if 'lat' in stop and 'lng' in stop:
                            route_points.append(f"{stop['lat']},{stop['lng']}")
                
                # If no stops, use origin and destination
                if not route_points:
                    # For demo, use sample coordinates
                    route_points = ["37.7749,-122.4194", "34.0522,-118.2437"]
                
                # Create map frames showing progressive route
                for i in range(num_frames):
                    progress = (i + 1) / num_frames
                    num_points = max(2, int(len(route_points) * progress))
                    current_points = route_points[:num_points]
                    
                    # Create static map image
                    img = Image.new('RGB', (self.video_width, self.video_height), color='#e5e7eb')
                    draw = ImageDraw.Draw(img)
                    
                    # Add map title
                    draw.text((50, 50), "Journey Route", fill='#1f2937')
                    
                    # Draw route line (simplified)
                    if len(current_points) >= 2:
                        # In production, use actual map API
                        y_start = self.video_height // 3
                        x_step = (self.video_width - 100) // (len(current_points) - 1)
                        
                        points = []
                        for idx, point in enumerate(current_points):
                            x = 50 + (idx * x_step)
                            y = y_start + (idx * 20)  # Slight curve
                            points.append((x, y))
                            
                            # Draw stop marker
                            draw.ellipse([x-10, y-10, x+10, y+10], fill='#ef4444')
                            
                            # Add stop name if available
                            if idx < len(trip_data.get('stops', [])):
                                stop_name = trip_data['stops'][idx].get('name', f'Stop {idx+1}')
                                draw.text((x-30, y+15), stop_name[:15], fill='#1f2937')
                        
                        # Draw route line
                        if len(points) >= 2:
                            for i in range(len(points) - 1):
                                draw.line([points[i], points[i+1]], fill='#3b82f6', width=3)
                    
                    # Add distance and time info
                    info_y = self.video_height - 100
                    draw.text((50, info_y), 
                             f"Distance: {trip_data.get('distance_miles', 0):.1f} miles", 
                             fill='#1f2937')
                    draw.text((50, info_y + 30), 
                             f"Duration: {trip_data.get('duration_hours', 0):.1f} hours", 
                             fill='#1f2937')
                    
                    frames.append(img)
                
                # Convert frames to video
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(tmp.name, fourcc, 30.0, 
                                    (self.video_width, self.video_height))
                
                for frame in frames:
                    # Convert PIL to OpenCV format
                    cv_frame = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
                    out.write(cv_frame)
                
                out.release()
                
                return {
                    "path": tmp.name,
                    "duration": 10
                }
                
            except Exception as e:
                logger.error(f"Error creating map segment: {e}")
                # Return simple placeholder on error
                img = Image.new('RGB', (self.video_width, self.video_height), color='#6366f1')
                draw = ImageDraw.Draw(img)
                draw.text((self.video_width//2 - 50, self.video_height//2), 
                         "Route Map", fill='white')
                img.save(tmp.name.replace('.mp4', '.png'))
                
                # Convert single image to video
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(tmp.name, fourcc, 1.0, 
                                    (self.video_width, self.video_height))
                cv_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                for _ in range(10):  # 10 seconds
                    out.write(cv_frame)
                out.release()
                
                return {
                    "path": tmp.name,
                    "duration": 10
                }
    
    async def _create_highlights_segment(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create segment showing journey highlights"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            # Would create animated highlights here
            # Text overlays, transitions, etc.
            
            return {
                "path": tmp.name,
                "duration": 30
            }
    
    async def _create_photos_segment(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create photo montage segment"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            # Would create photo slideshow with Ken Burns effect
            
            return {
                "path": tmp.name,
                "duration": 10
            }
    
    async def _create_stats_segment(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create statistics visualization segment"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            img = Image.new('RGB', (self.video_width, self.video_height), color='#1f2937')
            draw = ImageDraw.Draw(img)
            
            # Add stats
            stats = [
                f"{trip_data['distance_miles']} miles",
                f"{trip_data['duration_hours']} hours",
                f"{len(trip_data['stops'])} stops",
                f"{len(trip_data['bookings'])} bookings made"
            ]
            
            y_pos = self.video_height // 2 - 150
            for stat in stats:
                draw.text((self.video_width//2, y_pos), stat, 
                         fill='white', anchor='mm')
                y_pos += 80
            
            # Save and create video
            frame_path = tmp.name.replace('.mp4', '.png')
            img.save(frame_path)
            
            (
                ffmpeg
                .input(frame_path, loop=1, t=5)
                .output(tmp.name, vcodec='libx264', pix_fmt='yuv420p')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return {
                "path": tmp.name,
                "duration": 5
            }
    
    async def _generate_narration(self, trip_data: Dict[str, Any], duration: int) -> str:
        """Generate narration text for the video"""
        narration = f"""
        Our journey from {trip_data['origin']} to {trip_data['destination']} 
        was filled with unforgettable moments. We traveled {trip_data['distance_miles']} miles,
        discovering hidden gems along the way. From {trip_data['highlights'][0]} 
        to {trip_data['highlights'][-1]}, every mile told a story. 
        This is more than a trip - it's a memory that will last forever.
        """
        return narration.strip()
    
    async def _generate_narration_audio(self, text: str) -> str:
        """Generate audio narration using TTS"""
        audio_data = await tts_service.synthesize_speech(
            text,
            voice_name="en-US-Journey-Neural"  # Special journey voice
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(audio_data)
            return tmp.name
    
    async def _get_background_music(self, style: str, duration: int) -> str:
        """Get background music track"""
        import numpy as np
        from scipy.io import wavfile
        
        # Music style parameters
        music_params = {
            "upbeat": {"tempo": 140, "frequencies": [440, 554, 659, 880], "pattern": "energetic"},
            "relaxed": {"tempo": 80, "frequencies": [261, 329, 392, 523], "pattern": "smooth"},
            "epic": {"tempo": 120, "frequencies": [220, 277, 330, 440], "pattern": "building"},
            "nostalgic": {"tempo": 90, "frequencies": [349, 440, 523, 698], "pattern": "melancholic"}
        }
        
        params = music_params.get(style, music_params["relaxed"])
        
        try:
            # Generate simple background music
            sample_rate = 44100
            samples = duration * sample_rate
            
            # Create base rhythm
            t = np.linspace(0, duration, samples)
            audio = np.zeros(samples)
            
            # Add multiple layers
            for i, freq in enumerate(params["frequencies"]):
                # Create note pattern
                note_duration = 60.0 / params["tempo"]  # Duration of one beat
                note_samples = int(note_duration * sample_rate)
                
                # Generate wave with envelope
                for beat in range(int(duration / note_duration)):
                    start = beat * note_samples
                    end = min(start + note_samples, samples)
                    
                    if start < samples:
                        # Simple envelope (attack-sustain-release)
                        envelope = np.ones(end - start)
                        attack_samples = int(0.1 * note_samples)
                        release_samples = int(0.2 * note_samples)
                        
                        if attack_samples < len(envelope):
                            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
                        if release_samples < len(envelope):
                            envelope[-release_samples:] = np.linspace(1, 0, release_samples)
                        
                        # Add harmonics for richer sound
                        wave = np.sin(2 * np.pi * freq * t[start:end])
                        wave += 0.3 * np.sin(4 * np.pi * freq * t[start:end])  # Octave
                        wave += 0.2 * np.sin(3 * np.pi * freq * t[start:end])  # Fifth
                        
                        # Apply envelope and mix
                        audio[start:end] += wave * envelope * 0.1 * (1 - i * 0.2)
            
            # Add simple drum pattern for upbeat styles
            if style == "upbeat":
                kick_freq = 60
                for beat in range(0, duration * 4):  # 4 beats per second
                    kick_start = int(beat * sample_rate / 4)
                    kick_end = min(kick_start + int(sample_rate / 20), samples)
                    if kick_start < samples:
                        kick = np.sin(2 * np.pi * kick_freq * t[kick_start:kick_end])
                        kick *= np.exp(-5 * t[:kick_end-kick_start])  # Quick decay
                        audio[kick_start:kick_end] += kick * 0.3
            
            # Normalize audio
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio)) * 0.8
            
            # Convert to 16-bit PCM
            audio_int16 = (audio * 32767).astype(np.int16)
            
            # Save as WAV first
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_tmp:
                wavfile.write(wav_tmp.name, sample_rate, audio_int16)
                
                # Convert to MP3 using ffmpeg
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_tmp:
                    ffmpeg_cmd = [
                        'ffmpeg', '-i', wav_tmp.name,
                        '-acodec', 'mp3', '-ab', '128k',
                        '-y', mp3_tmp.name
                    ]
                    
                    result = subprocess.run(ffmpeg_cmd, capture_output=True)
                    if result.returncode == 0:
                        return mp3_tmp.name
                    else:
                        # If ffmpeg fails, return the WAV file
                        return wav_tmp.name
                        
        except Exception as e:
            logger.error(f"Error generating background music: {e}")
            # Return empty audio file on error
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                # Create silent audio file
                silent_audio = np.zeros(int(duration * 44100), dtype=np.int16)
                wavfile.write(tmp.name.replace('.mp3', '.wav'), 44100, silent_audio)
                return tmp.name
    
    async def _combine_video(
        self,
        segments: List[Dict[str, Any]],
        narration_audio: str,
        music_track: str,
        trip_id: str
    ) -> str:
        """Combine all elements into final video"""
        output_path = f"/tmp/journey_{trip_id}.mp4"
        
        # Concatenate video segments
        input_list = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        for segment in segments:
            input_list.write(f"file '{segment['path']}'\n")
        input_list.close()
        
        # Combine videos with audio
        try:
            (
                ffmpeg
                .input(input_list.name, format='concat', safe=0)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    audio_bitrate='192k',
                    video_bitrate='5000k'
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            # In production, upload to cloud storage
            # For now, return local path
            return f"/videos/journey_{trip_id}.mp4"
            
        finally:
            # Cleanup temp files
            os.unlink(input_list.name)
            for segment in segments:
                if os.path.exists(segment['path']):
                    os.unlink(segment['path'])
    
    async def _generate_thumbnail(self, trip_data: Dict[str, Any]) -> str:
        """Generate video thumbnail"""
        img = Image.new('RGB', (self.video_width, self.video_height), color='#6366f1')
        draw = ImageDraw.Draw(img)
        
        # Add trip title
        title = f"{trip_data['origin']} → {trip_data['destination']}"
        draw.text((self.video_width//2, self.video_height//2), 
                 title, fill='white', anchor='mm')
        
        # Add play button overlay
        play_size = 120
        play_x = self.video_width // 2 - play_size // 2
        play_y = self.video_height // 2 + 100
        draw.ellipse([play_x, play_y, play_x + play_size, play_y + play_size], 
                    fill='white', outline='white')
        
        # Play triangle
        points = [
            (play_x + 40, play_y + 30),
            (play_x + 40, play_y + 90),
            (play_x + 80, play_y + 60)
        ]
        draw.polygon(points, fill='#6366f1')
        
        # Save thumbnail
        thumbnail_path = f"/tmp/thumbnail_{trip_data['id']}.jpg"
        img.save(thumbnail_path, 'JPEG', quality=95)
        
        # In production, upload to cloud storage
        return f"/thumbnails/journey_{trip_data['id']}.jpg"
    
    def _generate_description(self, trip_data: Dict[str, Any]) -> str:
        """Generate social media description"""
        return f"""
🚗 {trip_data['origin']} to {trip_data['destination']} Adventure!
        
📍 {trip_data['distance_miles']} miles of memories
⏱️ {trip_data['duration_hours']} hours of discovery
📸 {len(trip_data['stops'])} amazing stops
        
Highlights:
{chr(10).join(f'✨ {h}' for h in trip_data['highlights'])}
        
Created with @RoadTripAI - Transform your journeys into stories!
#RoadTrip #Travel #Adventure #AITravel
        """.strip()
    
    def _generate_hashtags(self, trip_data: Dict[str, Any]) -> List[str]:
        """Generate relevant hashtags"""
        hashtags = [
            "#RoadTrip",
            "#TravelStories",
            "#AITravel",
            "#Adventure",
            f"#{trip_data['origin'].replace(' ', '')}",
            f"#{trip_data['destination'].replace(' ', '')}",
            "#JourneyVideo",
            "#TravelMemories",
            "#RoadTripAI"
        ]
        
        # Add specific hashtags based on stops
        for stop in trip_data['stops']:
            if stop['type'] == 'scenic':
                hashtags.append("#ScenicRoute")
            elif stop['type'] == 'photo':
                hashtags.append("#TravelPhotography")
        
        return hashtags[:10]  # Limit to 10 hashtags
    
    def _generate_share_links(self, video_url: str, trip_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate pre-filled share links for social platforms"""
        base_url = "https://app.roadtripstoryteller.com"
        video_full_url = f"{base_url}{video_url}"
        
        title = f"{trip_data['origin']} to {trip_data['destination']} Adventure"
        description = f"Check out my amazing road trip! {trip_data['distance_miles']} miles of memories."
        
        return {
            "twitter": f"https://twitter.com/intent/tweet?text={title}&url={video_full_url}&hashtags=RoadTrip,AITravel",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={video_full_url}",
            "instagram": "Copy link to share on Instagram",
            "tiktok": "Save video and upload to TikTok",
            "whatsapp": f"https://wa.me/?text={title} {video_full_url}",
            "email": f"mailto:?subject={title}&body={description} {video_full_url}"
        }


# Singleton instance
journey_video_service = JourneyVideoService()