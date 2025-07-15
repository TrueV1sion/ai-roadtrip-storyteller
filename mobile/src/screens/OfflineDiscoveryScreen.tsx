import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  FlatList,
  Dimensions,
  TouchableOpacity,
  Image,
} from 'react-native';
import {
  Text,
  Surface,
  Button,
  Searchbar,
  Chip,
  ProgressBar,
  ActivityIndicator,
  Divider,
  List,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

import { COLORS, SPACING } from '../theme';
import OfflineManager from '../services/OfflineManager';
import { formatBytes, formatDistance } from '../utils/formatters';
import { useTranslation } from '../i18n';
import { useAccessibility } from '../services/AccessibilityProvider';

const { width } = Dimensions.get('window');

const OfflineDiscoveryScreen: React.FC = () => {
  const navigation = useNavigation();
  const { t } = useTranslation();
  const { getFontScale } = useAccessibility();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [storageStats, setStorageStats] = useState<any>(null);
  const [downloadedMaps, setDownloadedMaps] = useState<any[]>([]);
  const [downloadedRoutes, setDownloadedRoutes] = useState<any[]>([]);
  const [downloadedContent, setDownloadedContent] = useState<any[]>([]);
  const [popularAreas, setPopularAreas] = useState<any[]>([]);
  
  // Apply font scaling for accessibility
  const fontScale = getFontScale();
  const scaledFontSize = (size: number) => size * fontScale;
  
  // Fetch data when component mounts
  useEffect(() => {
    loadOfflineData();
    fetchPopularAreas();
  }, []);
  
  const loadOfflineData = async () => {
    try {
      setIsLoading(true);
      
      // Initialize OfflineManager
      await OfflineManager.initialize();
      
      // Load storage stats
      const stats = await OfflineManager.getStorageStats();
      setStorageStats(stats);
      
      // Load downloaded regions
      const regions = await OfflineManager.getDownloadedRegions();
      setDownloadedMaps(regions);
      
      // Load downloaded routes
      const routes = await OfflineManager.getDownloadedRoutes();
      setDownloadedRoutes(routes);
      
      // Load downloaded content (stories, etc.) - placeholder
      // In a real implementation, this would fetch from OfflineManager
      setDownloadedContent([
        { 
          id: '1', 
          type: 'story', 
          title: 'The History of Golden Gate', 
          location: { name: 'San Francisco, CA' },
          sizeBytes: 250000,
          thumbnail: 'https://via.placeholder.com/150',
        },
        { 
          id: '2', 
          type: 'story', 
          title: 'Lost Trails of Yosemite', 
          location: { name: 'Yosemite National Park, CA' },
          sizeBytes: 320000,
          thumbnail: 'https://via.placeholder.com/150',
        },
      ]);
    } catch (error) {
      console.error('Error loading offline data:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const fetchPopularAreas = async () => {
    // In a real implementation, this would fetch popular areas from an API
    // For demonstration, we'll use placeholder data
    setPopularAreas([
      {
        id: '1',
        name: 'California Coast',
        description: 'Pacific Coast Highway road trip with stunning views',
        thumbnail: 'https://via.placeholder.com/300x150',
        popularity: 98,
        sizeEstimate: 250 * 1024 * 1024, // 250MB
      },
      {
        id: '2',
        name: 'Grand Canyon',
        description: 'Explore the majestic Grand Canyon and surrounding areas',
        thumbnail: 'https://via.placeholder.com/300x150',
        popularity: 95,
        sizeEstimate: 180 * 1024 * 1024, // 180MB
      },
      {
        id: '3',
        name: 'Florida Keys',
        description: 'Island hopping adventure along the Overseas Highway',
        thumbnail: 'https://via.placeholder.com/300x150',
        popularity: 92,
        sizeEstimate: 200 * 1024 * 1024, // 200MB
      },
    ]);
  };
  
  // Filter content based on search and category
  const getFilteredContent = () => {
    // Combine all offline content
    let allContent = [
      ...downloadedMaps.map(map => ({ ...map, contentType: 'map' })),
      ...downloadedRoutes.map(route => ({ ...route, contentType: 'route' })),
      ...downloadedContent.map(content => ({ ...content, contentType: content.type })),
    ];
    
    // Filter by category if not "all"
    if (selectedCategory !== 'all') {
      allContent = allContent.filter(item => item.contentType === selectedCategory);
    }
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      allContent = allContent.filter(item => {
        // Maps
        if (item.contentType === 'map' && item.region) {
          return `${item.region.latitude}, ${item.region.longitude}`.toLowerCase().includes(query);
        }
        // Routes
        else if (item.contentType === 'route') {
          return (item.originName?.toLowerCase().includes(query) || 
                 item.destinationName?.toLowerCase().includes(query));
        }
        // Stories and other content
        else {
          return (item.title?.toLowerCase().includes(query) || 
                 item.location?.name?.toLowerCase().includes(query));
        }
      });
    }
    
    return allContent;
  };
  
  // Render header with storage info
  const renderHeader = () => (
    <Surface style={styles.statsContainer}>
      <Text style={[styles.statsTitle, { fontSize: scaledFontSize(18) }]}>
        {t('offline.storage.title')}
      </Text>
      
      {storageStats && (
        <>
          <View style={styles.storageBarContainer}>
            <View 
              style={[
                styles.storageBar, 
                { width: `${storageStats.percentUsed}%` },
                storageStats.percentUsed > 85 ? styles.storageBarWarning : null
              ]} 
            />
          </View>
          
          <Text style={[styles.storageText, { fontSize: scaledFontSize(14) }]}>
            {formatBytes(storageStats.totalStorageUsed)} {t('offline.storage.used')} {formatBytes(storageStats.maxStorage)}
            {' '}({Math.round(storageStats.percentUsed)}%)
          </Text>
        </>
      )}
      
      <View style={styles.actionsContainer}>
        <Button
          mode="contained"
          icon="map-plus"
          onPress={() => navigation.navigate('MapDownload' as never)}
          style={styles.downloadButton}
          accessibilityLabel={t('offline.download.title')}
        >
          {t('offline.download.title')}
        </Button>
        
        <Button
          mode="outlined"
          icon="cog"
          onPress={() => navigation.navigate('Offline' as never)}
          style={styles.settingsButton}
          accessibilityLabel={t('settings.title')}
        >
          {t('settings.title')}
        </Button>
      </View>
    </Surface>
  );
  
  // Render filters
  const renderFilters = () => (
    <View style={styles.filtersContainer}>
      <Searchbar
        placeholder={t('common.search')}
        onChangeText={setSearchQuery}
        value={searchQuery}
        style={styles.searchbar}
        accessibilityLabel={t('common.search')}
      />
      
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.categoriesScroll}
        contentContainerStyle={styles.categoriesContent}
      >
        {['all', 'map', 'route', 'story'].map(category => (
          <Chip
            key={category}
            selected={selectedCategory === category}
            onPress={() => setSelectedCategory(category)}
            style={styles.categoryChip}
            accessibilityLabel={`${t(`offline.filter.${category}`)} ${t('common.category')}`}
          >
            {t(`offline.filter.${category}`)}
          </Chip>
        ))}
      </ScrollView>
    </View>
  );
  
  // Render popular download areas section
  const renderPopularAreas = () => (
    <View style={styles.popularContainer}>
      <Text style={[styles.sectionTitle, { fontSize: scaledFontSize(18) }]}>
        {t('offline.popular.title')}
      </Text>
      
      <FlatList
        data={popularAreas}
        keyExtractor={item => item.id}
        horizontal
        showsHorizontalScrollIndicator={false}
        renderItem={({ item }) => (
          <TouchableOpacity 
            style={styles.popularCard}
            onPress={() => {
              // Navigate to a detailed view or start download
              // navigation.navigate('PopularAreaDetails' as never, { areaId: item.id } as never);
            }}
            accessibilityLabel={`${item.name}, ${item.description}`}
            accessibilityRole="button"
          >
            <Image 
              source={{ uri: item.thumbnail }}
              style={styles.popularImage}
              accessibilityLabel={item.name}
            />
            <View style={styles.popularOverlay}>
              <View style={styles.popularBadge}>
                <MaterialIcons name="favorite" size={12} color="#fff" />
                <Text style={styles.popularBadgeText}>{item.popularity}%</Text>
              </View>
            </View>
            <View style={styles.popularContent}>
              <Text style={[styles.popularTitle, { fontSize: scaledFontSize(16) }]}>
                {item.name}
              </Text>
              <Text style={[styles.popularDescription, { fontSize: scaledFontSize(14) }]} numberOfLines={2}>
                {item.description}
              </Text>
              <Text style={[styles.popularSize, { fontSize: scaledFontSize(12) }]}>
                {formatBytes(item.sizeEstimate)}
              </Text>
            </View>
          </TouchableOpacity>
        )}
        contentContainerStyle={styles.popularList}
      />
    </View>
  );
  
  // Render content list
  const renderContentList = () => {
    const filteredContent = getFilteredContent();
    
    if (filteredContent.length === 0) {
      return (
        <View style={styles.emptyState}>
          <MaterialIcons name="cloud-off" size={48} color={COLORS.border} />
          <Text style={[styles.emptyStateTitle, { fontSize: scaledFontSize(18) }]}>
            {t('offline.empty.title')}
          </Text>
          <Text style={[styles.emptyStateText, { fontSize: scaledFontSize(16) }]}>
            {t('offline.empty.description')}
          </Text>
          <Button
            mode="contained"
            icon="cloud-download"
            onPress={() => navigation.navigate('MapDownload' as never)}
            style={styles.emptyStateButton}
          >
            {t('offline.download.title')}
          </Button>
        </View>
      );
    }
    
    return (
      <View style={styles.contentListContainer}>
        <Text style={[styles.sectionTitle, { fontSize: scaledFontSize(18) }]}>
          {t('offline.downloadedMaps.title')} ({filteredContent.length})
        </Text>
        
        <FlatList
          data={filteredContent}
          keyExtractor={(item, index) => item.id || `item-${index}`}
          renderItem={({ item }) => {
            // Render based on content type
            if (item.contentType === 'map') {
              return (
                <Surface style={styles.contentCard}>
                  <View style={styles.contentIconContainer}>
                    <MaterialIcons name="map" size={32} color={COLORS.primary} />
                  </View>
                  <View style={styles.contentDetails}>
                    <Text style={[styles.contentTitle, { fontSize: scaledFontSize(16) }]}>
                      {t('offline.downloadedMaps.mapArea')} {item.region.latitude.toFixed(2)}, {item.region.longitude.toFixed(2)}
                    </Text>
                    <Text style={[styles.contentMeta, { fontSize: scaledFontSize(14) }]}>
                      {formatBytes(item.sizeBytes)} • {item.tileCount || 0} {t('offline.tiles')}
                    </Text>
                  </View>
                  <Button
                    icon="delete"
                    mode="text"
                    onPress={() => OfflineManager.deleteRegion(item.id)}
                    accessibilityLabel={t('common.delete')}
                  />
                </Surface>
              );
            } else if (item.contentType === 'route') {
              return (
                <Surface style={styles.contentCard}>
                  <View style={styles.contentIconContainer}>
                    <MaterialIcons name="directions" size={32} color={COLORS.secondary} />
                  </View>
                  <View style={styles.contentDetails}>
                    <Text style={[styles.contentTitle, { fontSize: scaledFontSize(16) }]}>
                      {item.originName} {t('offline.downloadedRoutes.to')} {item.destinationName}
                    </Text>
                    <Text style={[styles.contentMeta, { fontSize: scaledFontSize(14) }]}>
                      {formatBytes(item.sizeBytes)}
                    </Text>
                  </View>
                  <Button
                    icon="navigation"
                    mode="outlined"
                    onPress={() => {
                      // Navigate to this route
                      navigation.navigate('Navigation' as never, { routeId: item.id } as never);
                    }}
                    accessibilityLabel={t('navigation.startNavigation')}
                    style={styles.useButton}
                  >
                    {t('common.use')}
                  </Button>
                </Surface>
              );
            } else {
              // Story or other content
              return (
                <Surface style={styles.contentCard}>
                  <Image 
                    source={{ uri: item.thumbnail }}
                    style={styles.contentThumbnail}
                    accessibilityLabel={item.title}
                  />
                  <View style={styles.contentDetails}>
                    <Text style={[styles.contentTitle, { fontSize: scaledFontSize(16) }]}>
                      {item.title}
                    </Text>
                    <Text style={[styles.contentMeta, { fontSize: scaledFontSize(14) }]}>
                      {item.location.name} • {formatBytes(item.sizeBytes)}
                    </Text>
                  </View>
                  <Button
                    icon="book-open-variant"
                    mode="outlined"
                    onPress={() => {
                      // Navigate to this content
                      navigation.navigate('StoryViewer' as never, { storyId: item.id } as never);
                    }}
                    accessibilityLabel={t('offline.view')}
                    style={styles.useButton}
                  >
                    {t('offline.view')}
                  </Button>
                </Surface>
              );
            }
          }}
          contentContainerStyle={styles.contentList}
        />
      </View>
    );
  };
  
  // Render offline promotion if no content
  const renderPromotion = () => {
    const hasNoContent = downloadedMaps.length === 0 && 
                          downloadedRoutes.length === 0 && 
                          downloadedContent.length === 0;
    
    if (!hasNoContent) return null;
    
    return (
      <Surface style={styles.promoContainer}>
        <View style={styles.promoIconContainer}>
          <MaterialIcons name="cloud-download" size={64} color={COLORS.primary} />
        </View>
        
        <Text style={[styles.promoTitle, { fontSize: scaledFontSize(20) }]}>
          {t('offline.promo.title')}
        </Text>
        
        <Text style={[styles.promoDescription, { fontSize: scaledFontSize(16) }]}>
          {t('offline.promo.description')}
        </Text>
        
        <View style={styles.promoFeatures}>
          {[
            { icon: 'map', text: t('offline.promo.feature1') },
            { icon: 'navigation', text: t('offline.promo.feature2') },
            { icon: 'lightbulb', text: t('offline.promo.feature3') },
          ].map((feature, index) => (
            <View key={index} style={styles.promoFeatureItem}>
              <MaterialIcons name={feature.icon} size={18} color={COLORS.success} />
              <Text style={[styles.promoFeatureText, { fontSize: scaledFontSize(14) }]}>
                {feature.text}
              </Text>
            </View>
          ))}
        </View>
        
        <Button
          mode="contained"
          onPress={() => navigation.navigate('MapDownload' as never)}
          style={styles.promoButton}
          accessibilityLabel={t('offline.promo.cta')}
        >
          {t('offline.promo.cta')}
        </Button>
      </Surface>
    );
  };
  
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={[styles.loadingText, { fontSize: scaledFontSize(16) }]}>
          {t('common.loading')}
        </Text>
      </View>
    );
  }
  
  return (
    <ScrollView 
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      {renderHeader()}
      {renderFilters()}
      {renderPromotion()}
      {renderPopularAreas()}
      {renderContentList()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollContent: {
    paddingBottom: SPACING.large,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  loadingText: {
    marginTop: SPACING.small,
    fontSize: 16,
  },
  statsContainer: {
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 8,
  },
  statsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  storageBarContainer: {
    height: 12,
    backgroundColor: COLORS.surface,
    borderRadius: 6,
    overflow: 'hidden',
    marginBottom: SPACING.small,
  },
  storageBar: {
    height: '100%',
    backgroundColor: COLORS.primary,
    borderRadius: 6,
  },
  storageBarWarning: {
    backgroundColor: COLORS.warning,
  },
  storageText: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  actionsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  downloadButton: {
    flex: 1,
    marginRight: SPACING.small,
  },
  settingsButton: {
    flex: 1,
    marginLeft: SPACING.small,
  },
  filtersContainer: {
    paddingHorizontal: SPACING.medium,
    marginBottom: SPACING.medium,
  },
  searchbar: {
    marginBottom: SPACING.small,
    elevation: 2,
  },
  categoriesScroll: {
    flexDirection: 'row',
  },
  categoriesContent: {
    paddingVertical: SPACING.small,
  },
  categoryChip: {
    marginRight: SPACING.small,
  },
  popularContainer: {
    marginBottom: SPACING.large,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginHorizontal: SPACING.medium,
    marginBottom: SPACING.small,
  },
  popularList: {
    paddingHorizontal: SPACING.medium,
  },
  popularCard: {
    width: width * 0.7,
    marginRight: SPACING.medium,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: COLORS.surface,
    elevation: 2,
  },
  popularImage: {
    width: '100%',
    height: 120,
  },
  popularOverlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    padding: SPACING.small,
  },
  popularBadge: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: SPACING.small,
    paddingVertical: 2,
    borderRadius: 12,
    alignItems: 'center',
  },
  popularBadgeText: {
    color: '#fff',
    fontSize: 12,
    marginLeft: 2,
  },
  popularContent: {
    padding: SPACING.medium,
  },
  popularTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  popularDescription: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.small,
  },
  popularSize: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  contentListContainer: {
    marginBottom: SPACING.large,
  },
  contentList: {
    paddingHorizontal: SPACING.medium,
    paddingBottom: SPACING.large,
  },
  contentCard: {
    flexDirection: 'row',
    padding: SPACING.medium,
    marginBottom: SPACING.small,
    borderRadius: 8,
    alignItems: 'center',
  },
  contentIconContainer: {
    width: 48,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.medium,
  },
  contentThumbnail: {
    width: 48,
    height: 48,
    borderRadius: 4,
    marginRight: SPACING.medium,
  },
  contentDetails: {
    flex: 1,
    marginRight: SPACING.small,
  },
  contentTitle: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: SPACING.xsmall,
  },
  contentMeta: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  useButton: {
    minWidth: 80,
  },
  emptyState: {
    alignItems: 'center',
    padding: SPACING.large,
    marginHorizontal: SPACING.medium,
  },
  emptyStateTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: SPACING.medium,
    marginBottom: SPACING.small,
  },
  emptyStateText: {
    textAlign: 'center',
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  emptyStateButton: {
    marginTop: SPACING.small,
  },
  promoContainer: {
    margin: SPACING.medium,
    padding: SPACING.large,
    borderRadius: 12,
    alignItems: 'center',
  },
  promoIconContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: COLORS.primary + '15',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  promoTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: SPACING.small,
  },
  promoDescription: {
    fontSize: 16,
    textAlign: 'center',
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  promoFeatures: {
    width: '100%',
    marginBottom: SPACING.large,
  },
  promoFeatureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  promoFeatureText: {
    marginLeft: SPACING.small,
    fontSize: 14,
  },
  promoButton: {
    width: '100%',
  },
});

export default OfflineDiscoveryScreen; 