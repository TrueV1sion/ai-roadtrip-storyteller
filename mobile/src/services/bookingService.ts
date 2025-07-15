/**
 * Booking Service
 * 
 * Handles all booking-related operations
 * Integrates with voice orchestration for seamless experience
 */

import apiClient from './apiClient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { format } from 'date-fns';

export interface BookingItem {
  id: string;
  type: 'hotel' | 'restaurant' | 'activity';
  name: string;
  rating: number;
  price: number;
  image_url?: string;
  description: string;
  location: {
    lat: number;
    lng: number;
    address: string;
  };
  amenities?: string[];
  cuisine?: string;
  duration?: number;
  availability: BookingAvailability;
}

export interface BookingAvailability {
  available: boolean;
  slots?: string[];
  rooms?: number;
  message?: string;
}

export interface CreateBookingRequest {
  type: 'hotel' | 'restaurant' | 'activity';
  item_id: string;
  date: string;
  time?: string;
  party_size: number;
  nights?: number;
  special_requests?: string;
  payment_method?: string;
}

export interface Booking {
  id: string;
  confirmation_number: string;
  type: 'hotel' | 'restaurant' | 'activity';
  name: string;
  address: string;
  date: string;
  time?: string;
  party_size?: number;
  nights?: number;
  total_price: number;
  status: 'confirmed' | 'pending' | 'cancelled';
  contact_phone?: string;
  contact_email?: string;
  special_requests?: string;
  cancellation_policy?: string;
  created_at: string;
  qr_code?: string;
}

class BookingService {
  private static instance: BookingService;
  private bookingsCache: Map<string, Booking> = new Map();
  
  private constructor() {}
  
  static getInstance(): BookingService {
    if (!BookingService.instance) {
      BookingService.instance = new BookingService();
    }
    return BookingService.instance;
  }

  /**
   * Search for available bookings based on type and criteria
   */
  async searchBookings(
    type: 'hotel' | 'restaurant' | 'activity',
    criteria: {
      location?: { lat: number; lng: number };
      date?: Date;
      party_size?: number;
      radius_miles?: number;
      price_range?: { min: number; max: number };
      amenities?: string[];
      cuisine?: string;
      rating_min?: number;
    }
  ): Promise<BookingItem[]> {
    try {
      const params: any = {
        type,
        ...criteria,
        date: criteria.date ? format(criteria.date, 'yyyy-MM-dd') : undefined,
      };

      const response = await apiClient.get('/api/booking/search', { params });
      return response.data.results;
    } catch (error) {
      console.error('Search bookings failed:', error);
      throw error;
    }
  }

  /**
   * Get recommendations based on user preferences and context
   */
  async getRecommendations(
    type: 'hotel' | 'restaurant' | 'activity',
    context?: {
      time_of_day?: string;
      weather?: string;
      user_preferences?: any;
    }
  ): Promise<BookingItem[]> {
    try {
      const response = await apiClient.get(`/api/booking/recommendations/${type}`, {
        params: context,
      });
      return response.data.items;
    } catch (error) {
      console.error('Get recommendations failed:', error);
      throw error;
    }
  }

  /**
   * Check availability for a specific item
   */
  async checkAvailability(
    itemId: string,
    date: Date,
    partySize: number = 1
  ): Promise<BookingAvailability> {
    try {
      const response = await apiClient.post('/api/booking/availability', {
        item_id: itemId,
        date: format(date, 'yyyy-MM-dd'),
        party_size: partySize,
      });
      return response.data;
    } catch (error) {
      console.error('Check availability failed:', error);
      throw error;
    }
  }

  /**
   * Create a new booking
   */
  async createBooking(request: CreateBookingRequest): Promise<Booking> {
    try {
      const response = await apiClient.post('/api/booking/create', request);
      
      if (response.data.success) {
        const booking = response.data.booking;
        
        // Cache the booking
        this.bookingsCache.set(booking.id, booking);
        
        // Save to local storage
        await this.saveBookingLocally(booking);
        
        return booking;
      } else {
        throw new Error(response.data.message || 'Booking failed');
      }
    } catch (error) {
      console.error('Create booking failed:', error);
      throw error;
    }
  }

  /**
   * Get user's bookings
   */
  async getMyBookings(
    filter?: 'upcoming' | 'past' | 'all'
  ): Promise<Booking[]> {
    try {
      const response = await apiClient.get('/api/booking/my-bookings', {
        params: { filter },
      });
      
      const bookings = response.data.bookings;
      
      // Update cache
      bookings.forEach((booking: Booking) => {
        this.bookingsCache.set(booking.id, booking);
      });
      
      return bookings;
    } catch (error) {
      console.error('Get my bookings failed:', error);
      
      // Fallback to local storage
      return this.getLocalBookings(filter);
    }
  }

  /**
   * Get a specific booking by ID
   */
  async getBooking(bookingId: string): Promise<Booking | null> {
    // Check cache first
    if (this.bookingsCache.has(bookingId)) {
      return this.bookingsCache.get(bookingId)!;
    }

    try {
      const response = await apiClient.get(`/api/booking/${bookingId}`);
      const booking = response.data;
      
      // Update cache
      this.bookingsCache.set(booking.id, booking);
      
      return booking;
    } catch (error) {
      console.error('Get booking failed:', error);
      return null;
    }
  }

  /**
   * Cancel a booking
   */
  async cancelBooking(bookingId: string, reason?: string): Promise<boolean> {
    try {
      const response = await apiClient.post(`/api/booking/${bookingId}/cancel`, {
        reason,
      });
      
      if (response.data.success) {
        // Update cache
        const booking = this.bookingsCache.get(bookingId);
        if (booking) {
          booking.status = 'cancelled';
          await this.saveBookingLocally(booking);
        }
        
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Cancel booking failed:', error);
      throw error;
    }
  }

  /**
   * Modify a booking
   */
  async modifyBooking(
    bookingId: string,
    modifications: Partial<CreateBookingRequest>
  ): Promise<Booking> {
    try {
      const response = await apiClient.put(`/api/booking/${bookingId}`, modifications);
      
      if (response.data.success) {
        const updatedBooking = response.data.booking;
        
        // Update cache
        this.bookingsCache.set(updatedBooking.id, updatedBooking);
        await this.saveBookingLocally(updatedBooking);
        
        return updatedBooking;
      } else {
        throw new Error(response.data.message || 'Modification failed');
      }
    } catch (error) {
      console.error('Modify booking failed:', error);
      throw error;
    }
  }

  /**
   * Add booking to calendar
   */
  async addToCalendar(booking: Booking): Promise<boolean> {
    // This would integrate with the device calendar
    // Implementation depends on platform-specific calendar APIs
    console.log('Adding to calendar:', booking);
    return true;
  }

  /**
   * Share booking details
   */
  formatBookingForSharing(booking: Booking): string {
    const lines = [
      `${booking.type.charAt(0).toUpperCase() + booking.type.slice(1)} Booking`,
      `${booking.name}`,
      `📍 ${booking.address}`,
      `📅 ${format(new Date(booking.date), 'EEEE, MMMM d, yyyy')}`,
    ];

    if (booking.time) {
      lines.push(`🕐 ${booking.time}`);
    }

    if (booking.party_size) {
      lines.push(`👥 ${booking.party_size} guests`);
    }

    if (booking.nights) {
      lines.push(`🌙 ${booking.nights} nights`);
    }

    lines.push(
      ``,
      `Confirmation: ${booking.confirmation_number}`,
      `Total: $${booking.total_price}`
    );

    return lines.join('\n');
  }

  /**
   * Get booking suggestions based on context
   */
  async getContextualSuggestions(
    location: { lat: number; lng: number },
    context: {
      time_of_day: 'morning' | 'afternoon' | 'evening' | 'night';
      weather?: string;
      driving_duration?: number;
      previous_bookings?: string[];
    }
  ): Promise<{
    type: 'hotel' | 'restaurant' | 'activity';
    reason: string;
    items: BookingItem[];
  }[]> {
    try {
      const response = await apiClient.post('/api/booking/contextual-suggestions', {
        location,
        context,
      });
      
      return response.data.suggestions;
    } catch (error) {
      console.error('Get contextual suggestions failed:', error);
      return [];
    }
  }

  /**
   * Local storage operations
   */
  private async saveBookingLocally(booking: Booking): Promise<void> {
    try {
      const bookings = await this.getLocalBookings();
      const index = bookings.findIndex(b => b.id === booking.id);
      
      if (index >= 0) {
        bookings[index] = booking;
      } else {
        bookings.push(booking);
      }
      
      await AsyncStorage.setItem('@bookings', JSON.stringify(bookings));
    } catch (error) {
      console.error('Save booking locally failed:', error);
    }
  }

  private async getLocalBookings(filter?: 'upcoming' | 'past' | 'all'): Promise<Booking[]> {
    try {
      const stored = await AsyncStorage.getItem('@bookings');
      if (!stored) return [];
      
      const bookings: Booking[] = JSON.parse(stored);
      const now = new Date();
      
      switch (filter) {
        case 'upcoming':
          return bookings.filter(b => new Date(b.date) >= now && b.status !== 'cancelled');
        case 'past':
          return bookings.filter(b => new Date(b.date) < now);
        case 'all':
        default:
          return bookings;
      }
    } catch (error) {
      console.error('Get local bookings failed:', error);
      return [];
    }
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.bookingsCache.clear();
  }
}

export const bookingService = BookingService.getInstance();
export default bookingService;