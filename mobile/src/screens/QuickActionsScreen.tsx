import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Linking,
  Alert,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import { SafeArea } from '../components/SafeArea';
import { Card } from '../components/Card';
import { Button } from '../components/Button';

interface QuickAction {
  name: string;
  location: { lat: number; lng: number };
  distance: number;
  type: string;
  details: any;
}

export const QuickActionsScreen: React.FC = () => {
  const route = useRoute();
  const navigation = useNavigation();
  const { actions, location } = route.params as { actions: QuickAction[]; location: any };
  
  const [selectedAction, setSelectedAction] = useState<QuickAction | null>(null);

  const handleActionPress = (action: QuickAction) => {
    setSelectedAction(action);
  };

  const handleNavigate = (action: QuickAction) => {
    // Open in maps app
    const url = `https://maps.google.com/maps?daddr=${action.location.lat},${action.location.lng}`;
    Linking.openURL(url).catch(() => {
      Alert.alert('Error', 'Unable to open maps');
    });
  };

  const handleQuickOrder = (action: QuickAction) => {
    if (action.details.has_mobile_order) {
      // In production, this would open the restaurant's ordering app/website
      Alert.alert(
        'Mobile Order',
        `Opening ${action.name} mobile ordering...`,
        [
          { text: 'Cancel', style: 'cancel' },
          { 
            text: 'Continue', 
            onPress: () => {
              // Simulated - would open actual ordering URL
              Linking.openURL('https://order.example.com');
            }
          }
        ]
      );
    } else {
      Alert.alert('Not Available', 'Mobile ordering not available for this location');
    }
  };

  const getIconName = (type: string) => {
    switch (type) {
      case 'restaurant':
        return 'food';
      case 'charging':
        return 'ev-station';
      case 'rest':
        return 'bed';
      case 'gas':
        return 'gas-station';
      default:
        return 'map-marker';
    }
  };

  const formatDistance = (meters: number) => {
    if (meters < 1000) {
      return `${meters}m`;
    }
    return `${(meters / 1000).toFixed(1)}km`;
  };

  const renderAction = ({ item }: { item: QuickAction }) => (
    <Card
      style={[
        styles.actionCard,
        selectedAction === item && styles.selectedCard
      ]}
      onPress={() => handleActionPress(item)}
    >
      <View style={styles.actionHeader}>
        <MaterialCommunityIcons
          name={getIconName(item.type)}
          size={32}
          color="#4A90E2"
        />
        <View style={styles.actionInfo}>
          <Text style={styles.actionName} numberOfLines={1}>
            {item.name}
          </Text>
          <Text style={styles.actionDistance}>
            {formatDistance(item.distance)} away
          </Text>
        </View>
      </View>

      {item.type === 'restaurant' && item.details && (
        <View style={styles.detailsRow}>
          {item.details.rating && (
            <View style={styles.ratingContainer}>
              <MaterialCommunityIcons name="star" size={16} color="#FFD700" />
              <Text style={styles.ratingText}>{item.details.rating}</Text>
            </View>
          )}
          {item.details.cuisine && (
            <Text style={styles.cuisineText}>{item.details.cuisine}</Text>
          )}
          {item.details.has_mobile_order && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>Mobile Order</Text>
            </View>
          )}
        </View>
      )}

      {item.type === 'charging' && item.details && (
        <View style={styles.detailsRow}>
          <Text style={styles.detailText}>
            Speed: {item.details.charging_speed}
          </Text>
          <Text style={styles.detailText}>
            Available: {item.details.available_ports} ports
          </Text>
        </View>
      )}

      {item.type === 'rest' && item.details && (
        <View style={styles.detailsRow}>
          <Text style={styles.detailText}>
            Amenities: {item.details.amenities?.join(', ')}
          </Text>
        </View>
      )}

      {selectedAction === item && (
        <View style={styles.actionButtons}>
          <Button
            title="Navigate"
            onPress={() => handleNavigate(item)}
            style={styles.navigateButton}
            size="small"
          />
          {item.type === 'restaurant' && item.details.has_mobile_order && (
            <Button
              title="Quick Order"
              onPress={() => handleQuickOrder(item)}
              style={styles.orderButton}
              size="small"
            />
          )}
        </View>
      )}
    </Card>
  );

  return (
    <SafeArea>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.title}>Quick Actions Nearby</Text>
          <View style={{ width: 24 }} />
        </View>

        <FlatList
          data={actions}
          renderItem={renderAction}
          keyExtractor={(item, index) => `${item.type}-${item.name}-${index}`}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            {actions.length} options found within 3km
          </Text>
        </View>
      </View>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  listContent: {
    padding: 15,
  },
  actionCard: {
    marginBottom: 15,
  },
  selectedCard: {
    borderColor: '#4A90E2',
    borderWidth: 2,
  },
  actionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  actionInfo: {
    flex: 1,
    marginLeft: 15,
  },
  actionName: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 2,
  },
  actionDistance: {
    fontSize: 14,
    color: '#666',
  },
  detailsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: 10,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 10,
  },
  ratingText: {
    marginLeft: 4,
    fontSize: 14,
    fontWeight: '600',
  },
  cuisineText: {
    fontSize: 14,
    color: '#666',
    marginRight: 10,
  },
  badge: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  badgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  detailText: {
    fontSize: 14,
    color: '#666',
    marginRight: 15,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  navigateButton: {
    flex: 1,
    marginRight: 5,
  },
  orderButton: {
    flex: 1,
    marginLeft: 5,
    backgroundColor: '#4CAF50',
  },
  footer: {
    padding: 20,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: '#666',
  },
});