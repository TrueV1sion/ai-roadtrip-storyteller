import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  FlatList,
  Platform
} from 'react-native';
import { FontAwesome5, MaterialIcons, Ionicons } from '@expo/vector-icons';
import { TrafficInfoType, TrafficIncidentType, RouteSegmentType } from '../../types/driving';

interface TrafficInfoPanelProps {
  trafficInfo: TrafficInfoType;
  onAlternateRouteSelected?: (routeId: string) => void;
  onClose: () => void;
}

const TrafficInfoPanel: React.FC<TrafficInfoPanelProps> = ({
  trafficInfo,
  onAlternateRouteSelected,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'incidents' | 'segments'>('overview');
  
  // Get color for traffic status
  const getTrafficStatusColor = (status: string) => {
    switch (status) {
      case 'minimal':
        return '#4CAF50';
      case 'light':
        return '#8BC34A';
      case 'moderate':
        return '#FFC107';
      case 'heavy':
        return '#FF9800';
      case 'severe':
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  };
  
  // Format time in minutes and seconds
  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${remainingSeconds}s`;
    }
  };
  
  // Format distance in km
  const formatDistance = (meters: number) => {
    return `${(meters / 1000).toFixed(1)} km`;
  };
  
  // Get icon and color for incident type
  const getIncidentTypeInfo = (type: string) => {
    switch (type) {
      case 'accident':
        return { icon: 'car-crash', color: '#F44336' };
      case 'construction':
        return { icon: 'hard-hat', color: '#FF9800' };
      case 'road_closure':
        return { icon: 'road', color: '#9C27B0' };
      case 'police':
        return { icon: 'shield-alt', color: '#2196F3' };
      case 'hazard':
        return { icon: 'exclamation-triangle', color: '#FFC107' };
      default:
        return { icon: 'info-circle', color: '#607D8B' };
    }
  };
  
  // Get color for severity
  const getSeverityColor = (severity: number) => {
    switch (severity) {
      case 1:
        return '#4CAF50';
      case 2:
        return '#8BC34A';
      case 3:
        return '#FFC107';
      case 4:
        return '#FF9800';
      case 5:
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  };
  
  // Render the overview tab
  const renderOverviewTab = () => {
    return (
      <View style={styles.tabContent}>
        <View style={styles.overviewCard}>
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Traffic Status</Text>
            <View style={[
              styles.statusBadge,
              { backgroundColor: getTrafficStatusColor(trafficInfo.overall_traffic) }
            ]}>
              <Text style={styles.statusText}>{trafficInfo.overall_traffic}</Text>
            </View>
          </View>
          
          <View style={styles.divider} />
          
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Total Distance</Text>
            <Text style={styles.overviewValue}>{formatDistance(trafficInfo.total_distance)}</Text>
          </View>
          
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Normal Time</Text>
            <Text style={styles.overviewValue}>{formatTime(trafficInfo.normal_duration)}</Text>
          </View>
          
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Current Time</Text>
            <Text style={styles.overviewValue}>{formatTime(trafficInfo.current_duration)}</Text>
          </View>
          
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Delay</Text>
            <Text style={[
              styles.overviewValue,
              trafficInfo.delay_seconds > 300 ? styles.delayText : null
            ]}>
              {formatTime(trafficInfo.delay_seconds)} ({trafficInfo.delay_percentage.toFixed(0)}%)
            </Text>
          </View>
        </View>
        
        {trafficInfo.incidents && trafficInfo.incidents.length > 0 && (
          <View style={styles.incidentsPreview}>
            <Text style={styles.sectionTitle}>Active Incidents ({trafficInfo.incidents.length})</Text>
            
            {trafficInfo.incidents.slice(0, 2).map((incident) => {
              const typeInfo = getIncidentTypeInfo(incident.type);
              
              return (
                <View key={incident.id} style={styles.incidentPreviewItem}>
                  <View style={[styles.incidentIcon, { backgroundColor: typeInfo.color }]}>
                    <FontAwesome5 name={typeInfo.icon} size={14} color="white" />
                  </View>
                  <Text style={styles.incidentPreviewText} numberOfLines={1}>
                    {incident.description}
                  </Text>
                </View>
              );
            })}
            
            {trafficInfo.incidents.length > 2 && (
              <TouchableOpacity
                style={styles.viewMoreButton}
                onPress={() => setActiveTab('incidents')}
              >
                <Text style={styles.viewMoreText}>View all incidents</Text>
              </TouchableOpacity>
            )}
          </View>
        )}
        
        {trafficInfo.alternate_routes && trafficInfo.alternate_routes.length > 0 && (
          <View style={styles.alternateRoutesSection}>
            <Text style={styles.sectionTitle}>Alternate Routes</Text>
            
            {trafficInfo.alternate_routes.map((route, index) => (
              <TouchableOpacity
                key={route.route_id}
                style={styles.alternateRouteCard}
                onPress={() => onAlternateRouteSelected && onAlternateRouteSelected(route.route_id)}
              >
                <View style={styles.routeHeader}>
                  <Text style={styles.routeTitle}>Route {index + 1}: {route.description}</Text>
                  <View style={[
                    styles.trafficBadge, 
                    { backgroundColor: getTrafficStatusColor(route.traffic_level) }
                  ]}>
                    <Text style={styles.trafficBadgeText}>{route.traffic_level}</Text>
                  </View>
                </View>
                
                <View style={styles.routeDetails}>
                  <View style={styles.routeMetric}>
                    <FontAwesome5 name="road" size={12} color="#2196F3" />
                    <Text style={styles.routeMetricText}>{formatDistance(route.distance)}</Text>
                  </View>
                  
                  <View style={styles.routeMetric}>
                    <FontAwesome5 name="clock" size={12} color="#4CAF50" />
                    <Text style={styles.routeMetricText}>{formatTime(route.duration)}</Text>
                  </View>
                  
                  <View style={styles.savingsContainer}>
                    <Text style={styles.savingsText}>
                      Save {formatTime(trafficInfo.current_duration - route.duration)}
                    </Text>
                  </View>
                </View>
                
                <MaterialIcons name="subdirectory-arrow-right" size={22} color="#2196F3" style={styles.routeIcon} />
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
    );
  };
  
  // Render the incidents tab
  const renderIncidentsTab = () => {
    if (!trafficInfo.incidents || trafficInfo.incidents.length === 0) {
      return (
        <View style={styles.emptyTabContent}>
          <MaterialIcons name="check-circle" size={48} color="#4CAF50" />
          <Text style={styles.emptyTabText}>No incidents reported</Text>
        </View>
      );
    }
    
    return (
      <FlatList
        data={trafficInfo.incidents}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => {
          const typeInfo = getIncidentTypeInfo(item.type);
          
          return (
            <View style={styles.incidentCard}>
              <View style={styles.incidentHeader}>
                <View style={[styles.incidentTypeContainer, { backgroundColor: typeInfo.color + '20' }]}>
                  <FontAwesome5 name={typeInfo.icon} size={16} color={typeInfo.color} />
                  <Text style={[styles.incidentType, { color: typeInfo.color }]}>
                    {item.type.replace('_', ' ')}
                  </Text>
                </View>
                
                <View style={[
                  styles.severityBadge,
                  { backgroundColor: getSeverityColor(item.severity) }
                ]}>
                  <Text style={styles.severityText}>Severity {item.severity}</Text>
                </View>
              </View>
              
              <Text style={styles.incidentDescription}>{item.description}</Text>
              
              <View style={styles.incidentDetails}>
                <Text style={styles.affectedRoads}>
                  <Text style={styles.detailLabel}>Roads: </Text>
                  {item.affected_roads.join(', ')}
                </Text>
                
                {item.delay_minutes !== undefined && (
                  <Text style={styles.delayInfo}>
                    <Text style={styles.detailLabel}>Delay: </Text>
                    {item.delay_minutes} min
                  </Text>
                )}
              </View>
            </View>
          );
        }}
      />
    );
  };
  
  // Render the segments tab
  const renderSegmentsTab = () => {
    if (!trafficInfo.segments || trafficInfo.segments.length === 0) {
      return (
        <View style={styles.emptyTabContent}>
          <MaterialIcons name="route" size={48} color="#9E9E9E" />
          <Text style={styles.emptyTabText}>No segment data available</Text>
        </View>
      );
    }
    
    return (
      <FlatList
        data={trafficInfo.segments}
        keyExtractor={(item) => item.segment_id}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => {
          const hasIncidents = item.incidents && item.incidents.length > 0;
          const trafficColor = getTrafficStatusColor(item.traffic_level);
          
          return (
            <View style={styles.segmentCard}>
              <View style={styles.segmentHeader}>
                <View style={[styles.trafficIndicator, { backgroundColor: trafficColor }]} />
                <Text style={styles.segmentTitle}>Segment {item.segment_id}</Text>
                <Text style={[styles.trafficLevel, { color: trafficColor }]}>
                  {item.traffic_level}
                </Text>
              </View>
              
              <View style={styles.segmentDetails}>
                <View style={styles.segmentMetric}>
                  <FontAwesome5 name="road" size={12} color="#2196F3" />
                  <Text style={styles.segmentMetricText}>{formatDistance(item.distance)}</Text>
                </View>
                
                <View style={styles.segmentMetric}>
                  <FontAwesome5 name="clock" size={12} color="#4CAF50" />
                  <Text style={styles.segmentMetricText}>
                    {formatTime(item.normal_duration)} → {formatTime(item.current_duration)}
                  </Text>
                </View>
                
                {item.speed_limit && (
                  <View style={styles.segmentMetric}>
                    <FontAwesome5 name="tachometer-alt" size={12} color="#FF9800" />
                    <Text style={styles.segmentMetricText}>{item.speed_limit} km/h</Text>
                  </View>
                )}
              </View>
              
              {hasIncidents && (
                <View style={styles.segmentIncidents}>
                  <Text style={styles.segmentIncidentsTitle}>
                    Incidents ({item.incidents.length})
                  </Text>
                  
                  {item.incidents.map((incident) => {
                    const typeInfo = getIncidentTypeInfo(incident.type);
                    
                    return (
                      <View key={incident.id} style={styles.segmentIncidentItem}>
                        <FontAwesome5 name={typeInfo.icon} size={12} color={typeInfo.color} style={styles.incidentItemIcon} />
                        <Text style={styles.incidentItemText} numberOfLines={1}>
                          {incident.description}
                        </Text>
                      </View>
                    );
                  })}
                </View>
              )}
            </View>
          );
        }}
      />
    );
  };
  
  // Render active tab content
  const renderActiveTab = () => {
    switch (activeTab) {
      case 'incidents':
        return renderIncidentsTab();
      case 'segments':
        return renderSegmentsTab();
      case 'overview':
      default:
        return renderOverviewTab();
    }
  };
  
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Traffic Information</Text>
        <TouchableOpacity style={styles.closeButton} onPress={onClose}>
          <Ionicons name="close" size={24} color="#333" />
        </TouchableOpacity>
      </View>
      
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'overview' && styles.activeTab]}
          onPress={() => setActiveTab('overview')}
        >
          <FontAwesome5 
            name="map" 
            size={16} 
            color={activeTab === 'overview' ? '#2196F3' : '#757575'} 
          />
          <Text 
            style={[
              styles.tabText, 
              activeTab === 'overview' && styles.activeTabText
            ]}
          >
            Overview
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'incidents' && styles.activeTab]}
          onPress={() => setActiveTab('incidents')}
        >
          <FontAwesome5 
            name="exclamation-triangle" 
            size={16} 
            color={activeTab === 'incidents' ? '#2196F3' : '#757575'} 
          />
          <Text 
            style={[
              styles.tabText, 
              activeTab === 'incidents' && styles.activeTabText
            ]}
          >
            Incidents ({trafficInfo.incidents?.length || 0})
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'segments' && styles.activeTab]}
          onPress={() => setActiveTab('segments')}
        >
          <FontAwesome5 
            name="road" 
            size={16} 
            color={activeTab === 'segments' ? '#2196F3' : '#757575'} 
          />
          <Text 
            style={[
              styles.tabText, 
              activeTab === 'segments' && styles.activeTabText
            ]}
          >
            Segments
          </Text>
        </TouchableOpacity>
      </View>
      
      {renderActiveTab()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    padding: 4,
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#2196F3',
  },
  tabText: {
    marginLeft: 6,
    fontSize: 14,
    color: '#757575',
  },
  activeTabText: {
    color: '#2196F3',
    fontWeight: 'bold',
  },
  tabContent: {
    flex: 1,
    padding: 16,
  },
  emptyTabContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  emptyTabText: {
    marginTop: 10,
    fontSize: 16,
    color: '#757575',
    textAlign: 'center',
  },
  listContent: {
    padding: 16,
  },
  overviewCard: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  overviewItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  overviewLabel: {
    fontSize: 14,
    color: '#757575',
  },
  overviewValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white',
    textTransform: 'uppercase',
  },
  divider: {
    height: 1,
    backgroundColor: '#e0e0e0',
    marginVertical: 10,
  },
  delayText: {
    color: '#F44336',
  },
  incidentsPreview: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  incidentPreviewItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  incidentIcon: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  incidentPreviewText: {
    flex: 1,
    fontSize: 14,
    color: '#333',
  },
  viewMoreButton: {
    alignItems: 'center',
    paddingVertical: 8,
    marginTop: 5,
  },
  viewMoreText: {
    fontSize: 14,
    color: '#2196F3',
    fontWeight: '500',
  },
  alternateRoutesSection: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  alternateRouteCard: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  routeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  routeTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  trafficBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  trafficBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: 'white',
    textTransform: 'uppercase',
  },
  routeDetails: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  routeMetric: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
  },
  routeMetricText: {
    fontSize: 12,
    color: '#757575',
    marginLeft: 4,
  },
  savingsContainer: {
    marginLeft: 'auto',
  },
  savingsText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  routeIcon: {
    position: 'absolute',
    right: 12,
    bottom: 10,
  },
  
  // Incident tab styles
  incidentCard: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  incidentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  incidentTypeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 16,
  },
  incidentType: {
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 6,
    textTransform: 'capitalize',
  },
  severityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  severityText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: 'white',
  },
  incidentDescription: {
    fontSize: 14,
    color: '#333',
    marginBottom: 8,
  },
  incidentDetails: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 8,
  },
  affectedRoads: {
    fontSize: 12,
    color: '#757575',
    marginBottom: 4,
  },
  delayInfo: {
    fontSize: 12,
    color: '#757575',
  },
  detailLabel: {
    fontWeight: 'bold',
    color: '#555',
  },
  
  // Segment tab styles
  segmentCard: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  segmentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  trafficIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 8,
  },
  segmentTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  trafficLevel: {
    fontSize: 12,
    fontWeight: '500',
    textTransform: 'uppercase',
  },
  segmentDetails: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  segmentMetric: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
    marginBottom: 4,
  },
  segmentMetricText: {
    fontSize: 12,
    color: '#757575',
    marginLeft: 4,
  },
  segmentIncidents: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 8,
  },
  segmentIncidentsTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#555',
    marginBottom: 6,
  },
  segmentIncidentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  incidentItemIcon: {
    marginRight: 6,
  },
  incidentItemText: {
    fontSize: 12,
    color: '#757575',
    flex: 1,
  },
});

export default TrafficInfoPanel;