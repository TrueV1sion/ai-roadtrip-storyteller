import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Image,
  Alert,
  RefreshControl,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { SafeArea } from '../SafeArea';
import { Card } from '../Card';
import { Button } from '../Button';
import { apiManager } from '../../services/api/apiManager';
import { theme } from '../../theme';

interface AirportAmenity {
  id: string;
  type: string;
  name: string;
  description: string;
  terminal: string;
  gate_area?: string;
  location_description: string;
  hours: Record<string, string>;
  amenities: string[];
  price_range?: string;
  rating?: number;
  reviews_count?: number;
  walking_time_minutes?: number;
  booking_status: string;
  booking_url?: string;
  commission_rate?: number;
  image_urls: string[];
  tags: string[];
}

interface AmenityRecommendation {
  category: string;
  reason: string;
  options: AirportAmenity[];
}

export const AirportAmenitiesScreen: React.FC = () => {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'all' | 'lounges' | 'dining' | 'recommended'>('recommended');
  const [amenities, setAmenities] = useState<AirportAmenity[]>([]);
  const [recommendations, setRecommendations] = useState<AmenityRecommendation[]>([]);
  const [waitTime, setWaitTime] = useState(120); // Mock 2-hour wait time
  const [userLocation, setUserLocation] = useState({ airport: 'LAX', terminal: '4' });

  useEffect(() => {
    loadAmenities();
  }, []);

  const loadAmenities = async () => {
    try {
      setLoading(true);

      // Fetch amenities and recommendations
      const [amenitiesResponse, recommendationsResponse] = await Promise.all([
        apiManager.get(`/api/airport/amenities/${userLocation.airport}`, {
          params: { terminal: userLocation.terminal },
        }),
        apiManager.get(`/api/airport/recommendations`, {
          params: {
            airport: userLocation.airport,
            terminal: userLocation.terminal,
            wait_time_minutes: waitTime,
          },
        }),
      ]);

      setAmenities(amenitiesResponse.data);
      setRecommendations(recommendationsResponse.data);
    } catch (error) {
      logger.error('Failed to load amenities:', error);
      Alert.alert('Error', 'Failed to load airport amenities');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadAmenities();
  };

  const getAmenityIcon = (type: string) => {
    switch (type) {
      case 'lounge':
        return 'sofa';
      case 'restaurant':
        return 'silverware-fork-knife';
      case 'cafe':
        return 'coffee';
      case 'bar':
        return 'glass-cocktail';
      case 'shop':
        return 'shopping';
      case 'spa':
        return 'spa';
      default:
        return 'star';
    }
  };

  const getFilteredAmenities = () => {
    switch (selectedTab) {
      case 'lounges':
        return amenities.filter(a => a.type === 'lounge');
      case 'dining':
        return amenities.filter(a => ['restaurant', 'cafe', 'bar'].includes(a.type));
      case 'recommended':
        return [];
      default:
        return amenities;
    }
  };

  const renderAmenityCard = (amenity: AirportAmenity) => (
    <TouchableOpacity
      key={amenity.id}
      onPress={() => navigation.navigate('AmenityDetails', { amenity })}
    >
      <Card style={styles.amenityCard}>
        <View style={styles.amenityHeader}>
          <View style={styles.amenityTitleRow}>
            <MaterialCommunityIcons
              name={getAmenityIcon(amenity.type)}
              size={24}
              color={theme.colors.primary}
              style={styles.amenityIcon}
            />
            <View style={styles.amenityInfo}>
              <Text style={styles.amenityName}>{amenity.name}</Text>
              <Text style={styles.amenityLocation}>
                {amenity.terminal} • {amenity.gate_area || amenity.location_description}
              </Text>
            </View>
          </View>
          {amenity.rating && (
            <View style={styles.ratingContainer}>
              <MaterialCommunityIcons name="star" size={16} color="#FFB800" />
              <Text style={styles.rating}>{amenity.rating.toFixed(1)}</Text>
            </View>
          )}
        </View>

        <Text style={styles.amenityDescription} numberOfLines={2}>
          {amenity.description}
        </Text>

        <View style={styles.amenityFeatures}>
          {amenity.amenities.slice(0, 3).map((feature, index) => (
            <View key={index} style={styles.featureChip}>
              <Text style={styles.featureText}>{feature}</Text>
            </View>
          ))}
          {amenity.amenities.length > 3 && (
            <Text style={styles.moreFeatures}>+{amenity.amenities.length - 3} more</Text>
          )}
        </View>

        <View style={styles.amenityFooter}>
          <View style={styles.footerInfo}>
            {amenity.walking_time_minutes && (
              <View style={styles.walkingTime}>
                <MaterialCommunityIcons name="walk" size={16} color={theme.colors.textSecondary} />
                <Text style={styles.walkingTimeText}>{amenity.walking_time_minutes} min</Text>
              </View>
            )}
            {amenity.price_range && (
              <Text style={styles.priceRange}>{amenity.price_range}</Text>
            )}
          </View>
          {amenity.booking_status === 'available' && (
            <Button
              title="Book"
              onPress={() => navigation.navigate('AmenityBooking', { amenity })}
              variant="primary"
              size="small"
            />
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );

  const renderRecommendations = () => (
    <ScrollView>
      {recommendations.map((rec, index) => (
        <View key={index} style={styles.recommendationSection}>
          <Text style={styles.recommendationCategory}>{rec.category}</Text>
          <Text style={styles.recommendationReason}>{rec.reason}</Text>
          {rec.options.map(amenity => renderAmenityCard(amenity))}
        </View>
      ))}
    </ScrollView>
  );

  const renderTabButton = (tab: typeof selectedTab, label: string, icon: string) => (
    <TouchableOpacity
      style={[styles.tabButton, selectedTab === tab && styles.tabButtonActive]}
      onPress={() => setSelectedTab(tab)}
    >
      <MaterialCommunityIcons
        name={icon}
        size={20}
        color={selectedTab === tab ? theme.colors.primary : theme.colors.textSecondary}
      />
      <Text style={[styles.tabLabel, selectedTab === tab && styles.tabLabelActive]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <SafeArea>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          <Text style={styles.loadingText}>Finding the best amenities for you...</Text>
        </View>
      </SafeArea>
    );
  }

  return (
    <SafeArea>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Airport Amenities</Text>
          <Text style={styles.subtitle}>
            {userLocation.airport} Terminal {userLocation.terminal} • {waitTime} min wait
          </Text>
        </View>

        <View style={styles.tabContainer}>
          {renderTabButton('recommended', 'For You', 'star')}
          {renderTabButton('all', 'All', 'view-grid')}
          {renderTabButton('lounges', 'Lounges', 'sofa')}
          {renderTabButton('dining', 'Dining', 'food')}
        </View>

        <ScrollView
          style={styles.content}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        >
          {selectedTab === 'recommended' ? (
            renderRecommendations()
          ) : (
            <View>
              {getFilteredAmenities().map(amenity => renderAmenityCard(amenity))}
            </View>
          )}
        </ScrollView>
      </View>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.textSecondary,
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  tabButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  tabButtonActive: {
    backgroundColor: theme.colors.primaryLight,
  },
  tabLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginLeft: 6,
  },
  tabLabelActive: {
    color: theme.colors.primary,
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: theme.colors.textSecondary,
  },
  recommendationSection: {
    marginBottom: 24,
    paddingHorizontal: 16,
  },
  recommendationCategory: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginTop: 16,
    marginBottom: 4,
  },
  recommendationReason: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 12,
  },
  amenityCard: {
    marginBottom: 12,
    padding: 16,
  },
  amenityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  amenityTitleRow: {
    flexDirection: 'row',
    flex: 1,
  },
  amenityIcon: {
    marginRight: 12,
  },
  amenityInfo: {
    flex: 1,
  },
  amenityName: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 2,
  },
  amenityLocation: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.backgroundLight,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  rating: {
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 4,
    color: theme.colors.text,
  },
  amenityDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 12,
    lineHeight: 20,
  },
  amenityFeatures: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  featureChip: {
    backgroundColor: theme.colors.backgroundLight,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 8,
    marginBottom: 8,
  },
  featureText: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  moreFeatures: {
    fontSize: 12,
    color: theme.colors.primary,
    marginTop: 4,
  },
  amenityFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  footerInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  walkingTime: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
  },
  walkingTimeText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginLeft: 4,
  },
  priceRange: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
  },
});