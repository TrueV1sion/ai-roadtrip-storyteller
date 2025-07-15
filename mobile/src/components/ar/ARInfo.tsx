import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  Animated,
  Dimensions,
  Platform
} from 'react-native';
import { RenderableARElement } from '../../types/ar';
import { FontAwesome5, MaterialIcons, AntDesign, Ionicons } from '@expo/vector-icons';

interface ARInfoProps {
  element: RenderableARElement;
  onClose: () => void;
}

const ARInfo: React.FC<ARInfoProps> = ({ element, onClose }) => {
  const { height } = Dimensions.get('window');
  const slideAnim = useRef(new Animated.Value(height)).current;
  
  useEffect(() => {
    Animated.spring(slideAnim, {
      toValue: 0,
      friction: 8,
      tension: 40,
      useNativeDriver: true
    }).start();
  }, []);
  
  const handleClose = () => {
    Animated.timing(slideAnim, {
      toValue: height,
      duration: 300,
      useNativeDriver: true
    }).start(() => {
      onClose();
    });
  };
  
  // Determine element type and customize UI accordingly
  const isHistorical = element.source_point_id?.includes('hist_');
  const isNavigation = element.source_point_id?.includes('nav_');
  const isNature = element.source_point_id?.includes('nat_');
  
  // Get appropriate title icon
  const getTitleIcon = () => {
    if (isHistorical) return <FontAwesome5 name="landmark" size={24} color={element.appearance.color} />;
    if (isNavigation) return <FontAwesome5 name="directions" size={24} color={element.appearance.color} />;
    if (isNature) return <MaterialIcons name="nature" size={24} color={element.appearance.color} />;
    return <FontAwesome5 name="info-circle" size={24} color={element.appearance.color} />;
  };
  
  // Get element-specific content
  const getElementSpecificContent = () => {
    if (isHistorical) {
      return (
        <View style={styles.specificContent}>
          <Text style={styles.yearText}>
            {element.appearance.year ? `Year: ${element.appearance.year}` : 'Historical Site'}
          </Text>
          
          {element.appearance.show_gallery && (
            <View style={styles.galleryContainer}>
              <Image 
                source={{ uri: 'https://example.com/historical_image.jpg' }} 
                style={styles.galleryImage}
              />
              <Text style={styles.imageCaption}>Historical view of this location</Text>
            </View>
          )}
          
          {element.appearance.comparison_view && (
            <TouchableOpacity style={styles.comparisonButton}>
              <FontAwesome5 name="sync-alt" size={16} color="white" />
              <Text style={styles.comparisonButtonText}>Compare Past & Present</Text>
            </TouchableOpacity>
          )}
        </View>
      );
    }
    
    if (isNavigation) {
      return (
        <View style={styles.specificContent}>
          <View style={styles.navigationInfo}>
            <View style={styles.navigationMetric}>
              <FontAwesome5 name="road" size={18} color={element.appearance.color} />
              <Text style={styles.metricValue}>
                {element.appearance.distance ? `${element.appearance.distance}m` : 'Ahead'}
              </Text>
            </View>
            
            {element.appearance.show_eta && (
              <View style={styles.navigationMetric}>
                <FontAwesome5 name="clock" size={18} color={element.appearance.color} />
                <Text style={styles.metricValue}>
                  {element.appearance.eta ? `${Math.round(parseInt(element.appearance.eta) / 60)}min` : 'Soon'}
                </Text>
              </View>
            )}
          </View>
          
          <View style={styles.directionContainer}>
            <FontAwesome5 
              name={
                element.appearance.arrow_type === 'right' ? 'arrow-alt-circle-right' :
                element.appearance.arrow_type === 'left' ? 'arrow-alt-circle-left' :
                element.appearance.arrow_type === 'uturn' ? 'undo-alt' :
                'arrow-alt-circle-up'
              } 
              size={32} 
              color={element.appearance.color} 
            />
            <Text style={styles.directionText}>{element.appearance.arrow_type || 'Continue'}</Text>
          </View>
          
          {element.appearance.path_preview && (
            <TouchableOpacity style={styles.previewButton}>
              <MaterialIcons name="preview" size={16} color="white" />
              <Text style={styles.previewButtonText}>Preview Route</Text>
            </TouchableOpacity>
          )}
        </View>
      );
    }
    
    if (isNature) {
      return (
        <View style={styles.specificContent}>
          {element.appearance.show_species && (
            <View style={styles.speciesContainer}>
              <Text style={styles.speciesLabel}>Species:</Text>
              <Text style={styles.speciesName}>{element.appearance.species || 'Unknown'}</Text>
            </View>
          )}
          
          {element.appearance.show_ecosystem_info && (
            <View style={styles.ecosystemContainer}>
              <Text style={styles.ecosystemTitle}>Ecosystem Information</Text>
              <Text style={styles.ecosystemDescription}>
                {element.appearance.ecosystem_info || 'Information not available'}
              </Text>
            </View>
          )}
          
          {element.appearance.show_conservation_status && (
            <View style={[
              styles.conservationContainer,
              element.appearance.conservation_status === 'Endangered' ? styles.endangered :
              element.appearance.conservation_status === 'Vulnerable' ? styles.vulnerable :
              element.appearance.conservation_status === 'Threatened' ? styles.threatened :
              styles.stable
            ]}>
              <Text style={styles.conservationLabel}>Conservation Status:</Text>
              <Text style={styles.conservationStatus}>
                {element.appearance.conservation_status || 'Not Evaluated'}
              </Text>
            </View>
          )}
          
          {element.appearance.camera_integration && (
            <TouchableOpacity style={styles.cameraButton}>
              <FontAwesome5 name="camera" size={16} color="white" />
              <Text style={styles.cameraButtonText}>Take Photo</Text>
            </TouchableOpacity>
          )}
        </View>
      );
    }
    
    // Default content for other element types
    return null;
  };
  
  return (
    <Animated.View 
      style={[
        styles.container,
        { transform: [{ translateY: slideAnim }] }
      ]}
    >
      <View style={styles.handle} />
      
      <View style={styles.header}>
        <View style={styles.titleContainer}>
          {getTitleIcon()}
          <Text style={styles.title}>{element.title || 'AR Point'}</Text>
        </View>
        
        <TouchableOpacity style={styles.closeButton} onPress={handleClose}>
          <AntDesign name="close" size={24} color="#666" />
        </TouchableOpacity>
      </View>
      
      <ScrollView style={styles.content}>
        <Text style={styles.description}>
          {element.description || 'No description available'}
        </Text>
        
        {getElementSpecificContent()}
        
        <View style={styles.actionsContainer}>
          <TouchableOpacity 
            style={[styles.actionButton, { backgroundColor: element.appearance.color }]}
          >
            <FontAwesome5 name="share-alt" size={16} color="white" />
            <Text style={styles.actionButtonText}>Share</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={[styles.actionButton, { backgroundColor: element.appearance.color }]}
          >
            <FontAwesome5 name="bookmark" size={16} color="white" />
            <Text style={styles.actionButtonText}>Save</Text>
          </TouchableOpacity>
          
          {element.interaction.audio_feedback && (
            <TouchableOpacity 
              style={[styles.actionButton, { backgroundColor: element.appearance.color }]}
            >
              <FontAwesome5 name="volume-up" size={16} color="white" />
              <Text style={styles.actionButtonText}>Listen</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '60%',
    backgroundColor: 'white',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: -3,
    },
    shadowOpacity: 0.27,
    shadowRadius: 4.65,
    elevation: 6,
  },
  handle: {
    width: 50,
    height: 5,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    alignSelf: 'center',
    marginTop: 10,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 10,
  },
  closeButton: {
    padding: 5,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  description: {
    fontSize: 16,
    lineHeight: 24,
    color: '#444',
    marginBottom: 20,
  },
  specificContent: {
    marginBottom: 20,
    padding: 15,
    backgroundColor: '#f9f9f9',
    borderRadius: 10,
  },
  yearText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#555',
    marginBottom: 10,
  },
  galleryContainer: {
    marginVertical: 10,
  },
  galleryImage: {
    width: '100%',
    height: 180,
    borderRadius: 10,
    backgroundColor: '#e0e0e0',
  },
  imageCaption: {
    fontSize: 14,
    color: '#777',
    fontStyle: 'italic',
    marginTop: 5,
  },
  comparisonButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#8C6D46',
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
  },
  comparisonButtonText: {
    color: 'white',
    marginLeft: 8,
    fontWeight: '600',
  },
  navigationInfo: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 15,
  },
  navigationMetric: {
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 5,
  },
  directionContainer: {
    alignItems: 'center',
    marginBottom: 15,
  },
  directionText: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 5,
    textTransform: 'capitalize',
  },
  previewButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4A90E2',
    padding: 12,
    borderRadius: 8,
  },
  previewButtonText: {
    color: 'white',
    marginLeft: 8,
    fontWeight: '600',
  },
  speciesContainer: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  speciesLabel: {
    fontSize: 16,
    fontWeight: 'bold',
    marginRight: 5,
  },
  speciesName: {
    fontSize: 16,
    fontStyle: 'italic',
  },
  ecosystemContainer: {
    marginVertical: 10,
  },
  ecosystemTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  ecosystemDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  conservationContainer: {
    marginVertical: 10,
    padding: 10,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  endangered: {
    backgroundColor: 'rgba(244, 67, 54, 0.1)',
  },
  vulnerable: {
    backgroundColor: 'rgba(255, 152, 0, 0.1)',
  },
  threatened: {
    backgroundColor: 'rgba(255, 235, 59, 0.1)',
  },
  stable: {
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
  },
  conservationLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    marginRight: 5,
  },
  conservationStatus: {
    fontSize: 14,
    fontWeight: '600',
  },
  cameraButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
  },
  cameraButtonText: {
    color: 'white',
    marginLeft: 8,
    fontWeight: '600',
  },
  actionsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 8,
  },
  actionButtonText: {
    color: 'white',
    marginLeft: 5,
    fontWeight: '600',
  },
});

export default ARInfo;