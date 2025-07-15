import { OfflineService } from '../offlineService';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import * as FileSystem from 'expo-file-system';
import { apiManager } from '../apiManager';

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage');
jest.mock('@react-native-community/netinfo');
jest.mock('expo-file-system');
jest.mock('../apiManager');

describe('OfflineService', () => {
  let offlineService: OfflineService;

  beforeEach(() => {
    jest.clearAllMocks();
    offlineService = new OfflineService();
    
    // Setup default mocks
    (NetInfo.fetch as jest.Mock).mockResolvedValue({
      isConnected: true,
      isInternetReachable: true,
    });
    
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    (AsyncStorage.setItem as jest.Mock).mockResolvedValue(undefined);
    (FileSystem.makeDirectoryAsync as jest.Mock).mockResolvedValue(undefined);
  });

  describe('Network Status', () => {
    it('should detect online status', async () => {
      const isOnline = await offlineService.isOnline();
      expect(isOnline).toBe(true);
    });

    it('should detect offline status', async () => {
      (NetInfo.fetch as jest.Mock).mockResolvedValue({
        isConnected: false,
        isInternetReachable: false,
      });
      
      const isOnline = await offlineService.isOnline();
      expect(isOnline).toBe(false);
    });

    it('should subscribe to network changes', () => {
      const callback = jest.fn();
      const unsubscribe = offlineService.onConnectionChange(callback);
      
      // Simulate network change
      const netInfoCallback = (NetInfo.addEventListener as jest.Mock).mock.calls[0][0];
      netInfoCallback({ isConnected: false });
      
      expect(callback).toHaveBeenCalledWith(false);
      
      unsubscribe();
    });
  });

  describe('Data Caching', () => {
    it('should cache API responses', async () => {
      const data = { id: 1, name: 'Test Story' };
      await offlineService.cacheData('stories/1', data);
      
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@offline_cache:stories/1',
        JSON.stringify({
          data,
          timestamp: expect.any(Number),
        })
      );
    });

    it('should retrieve cached data', async () => {
      const cachedData = {
        data: { id: 1, name: 'Test Story' },
        timestamp: Date.now(),
      };
      
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify(cachedData)
      );
      
      const result = await offlineService.getCachedData('stories/1');
      expect(result).toEqual(cachedData.data);
    });

    it('should expire old cache', async () => {
      const oldData = {
        data: { id: 1, name: 'Old Story' },
        timestamp: Date.now() - 8 * 24 * 60 * 60 * 1000, // 8 days old
      };
      
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify(oldData)
      );
      
      const result = await offlineService.getCachedData('stories/1');
      expect(result).toBeNull();
    });

    it('should clear all cache', async () => {
      const keys = [
        '@offline_cache:stories/1',
        '@offline_cache:stories/2',
        '@offline_cache:locations/1',
      ];
      
      (AsyncStorage.getAllKeys as jest.Mock).mockResolvedValue(keys);
      
      await offlineService.clearCache();
      
      expect(AsyncStorage.multiRemove).toHaveBeenCalledWith(keys);
    });
  });

  describe('Offline Queue', () => {
    it('should queue requests when offline', async () => {
      (NetInfo.fetch as jest.Mock).mockResolvedValue({
        isConnected: false,
      });
      
      await offlineService.queueRequest({
        method: 'POST',
        url: '/api/bookings',
        data: { hotelId: 'hotel-1' },
      });
      
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        expect.stringContaining('@offline_queue:'),
        expect.any(String)
      );
    });

    it('should process queue when online', async () => {
      const queuedRequest = {
        id: 'req-1',
        method: 'POST',
        url: '/api/bookings',
        data: { hotelId: 'hotel-1' },
      };
      
      (AsyncStorage.getAllKeys as jest.Mock).mockResolvedValue([
        '@offline_queue:req-1',
      ]);
      
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify(queuedRequest)
      );
      
      (apiManager.request as jest.Mock).mockResolvedValue({ data: { id: 'booking-1' } });
      
      await offlineService.processQueue();
      
      expect(apiManager.request).toHaveBeenCalledWith({
        method: 'POST',
        url: '/api/bookings',
        data: { hotelId: 'hotel-1' },
      });
      
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@offline_queue:req-1');
    });

    it('should handle queue processing errors', async () => {
      const queuedRequest = {
        id: 'req-1',
        method: 'POST',
        url: '/api/bookings',
        data: { hotelId: 'hotel-1' },
      };
      
      (AsyncStorage.getAllKeys as jest.Mock).mockResolvedValue([
        '@offline_queue:req-1',
      ]);
      
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify(queuedRequest)
      );
      
      (apiManager.request as jest.Mock).mockRejectedValue(new Error('Network error'));
      
      await offlineService.processQueue();
      
      // Should not remove failed request from queue
      expect(AsyncStorage.removeItem).not.toHaveBeenCalled();
    });
  });

  describe('File Downloads', () => {
    it('should download files for offline use', async () => {
      const fileUrl = 'https://example.com/map.jpg';
      const localPath = `${FileSystem.documentDirectory}offline/map.jpg`;
      
      (FileSystem.downloadAsync as jest.Mock).mockResolvedValue({
        uri: localPath,
      });
      
      const result = await offlineService.downloadFile(fileUrl, 'map.jpg');
      
      expect(FileSystem.makeDirectoryAsync).toHaveBeenCalledWith(
        `${FileSystem.documentDirectory}offline`,
        { intermediates: true }
      );
      
      expect(FileSystem.downloadAsync).toHaveBeenCalledWith(
        fileUrl,
        localPath
      );
      
      expect(result).toBe(localPath);
    });

    it('should handle download errors', async () => {
      (FileSystem.downloadAsync as jest.Mock).mockRejectedValue(
        new Error('Download failed')
      );
      
      await expect(
        offlineService.downloadFile('https://example.com/map.jpg', 'map.jpg')
      ).rejects.toThrow('Download failed');
    });

    it('should track download progress', async () => {
      const progressCallback = jest.fn();
      
      (FileSystem.createDownloadResumable as jest.Mock).mockReturnValue({
        downloadAsync: jest.fn().mockResolvedValue({ uri: 'local://path' }),
      });
      
      await offlineService.downloadFileWithProgress(
        'https://example.com/large-file.mp4',
        'video.mp4',
        progressCallback
      );
      
      expect(FileSystem.createDownloadResumable).toHaveBeenCalledWith(
        'https://example.com/large-file.mp4',
        expect.any(String),
        {},
        progressCallback
      );
    });
  });

  describe('Offline Maps', () => {
    it('should download map tiles for offline use', async () => {
      const region = {
        latitude: 40.7128,
        longitude: -74.0060,
        latitudeDelta: 0.1,
        longitudeDelta: 0.1,
      };
      
      (FileSystem.downloadAsync as jest.Mock).mockResolvedValue({
        uri: 'local://tile',
      });
      
      await offlineService.downloadMapRegion(region);
      
      // Should download multiple tiles
      expect(FileSystem.downloadAsync).toHaveBeenCalledTimes(expect.any(Number));
      
      // Should save region metadata
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        expect.stringContaining('@offline_maps:'),
        expect.any(String)
      );
    });

    it('should list downloaded map regions', async () => {
      const regions = [
        { id: 'region-1', name: 'New York', bounds: {} },
        { id: 'region-2', name: 'Los Angeles', bounds: {} },
      ];
      
      (AsyncStorage.getAllKeys as jest.Mock).mockResolvedValue([
        '@offline_maps:region-1',
        '@offline_maps:region-2',
      ]);
      
      (AsyncStorage.multiGet as jest.Mock).mockResolvedValue([
        ['@offline_maps:region-1', JSON.stringify(regions[0])],
        ['@offline_maps:region-2', JSON.stringify(regions[1])],
      ]);
      
      const result = await offlineService.getDownloadedMapRegions();
      
      expect(result).toEqual(regions);
    });

    it('should delete map region', async () => {
      const regionId = 'region-1';
      const regionData = {
        id: regionId,
        tiles: ['tile1.jpg', 'tile2.jpg'],
      };
      
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify(regionData)
      );
      
      (FileSystem.deleteAsync as jest.Mock).mockResolvedValue(undefined);
      
      await offlineService.deleteMapRegion(regionId);
      
      // Should delete tile files
      expect(FileSystem.deleteAsync).toHaveBeenCalledTimes(2);
      
      // Should remove metadata
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith(
        `@offline_maps:${regionId}`
      );
    });
  });

  describe('Sync Management', () => {
    it('should track sync status', async () => {
      const syncData = {
        lastSync: Date.now(),
        pendingChanges: 5,
      };
      
      await offlineService.updateSyncStatus(syncData);
      
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@sync_status',
        JSON.stringify(syncData)
      );
    });

    it('should get sync status', async () => {
      const syncData = {
        lastSync: Date.now() - 3600000, // 1 hour ago
        pendingChanges: 3,
      };
      
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify(syncData)
      );
      
      const status = await offlineService.getSyncStatus();
      
      expect(status).toEqual(syncData);
    });

    it('should perform full sync when online', async () => {
      const pendingRequests = [
        { id: 'req-1', method: 'POST', url: '/api/data' },
      ];
      
      (AsyncStorage.getAllKeys as jest.Mock).mockResolvedValue([
        '@offline_queue:req-1',
      ]);
      
      await offlineService.performSync();
      
      expect(apiManager.request).toHaveBeenCalled();
      
      // Should update sync status
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@sync_status',
        expect.stringContaining('lastSync')
      );
    });
  });

  describe('Storage Management', () => {
    it('should calculate offline storage size', async () => {
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        size: 1024 * 1024 * 50, // 50MB
      });
      
      const size = await offlineService.getOfflineStorageSize();
      
      expect(size).toBe(1024 * 1024 * 50);
    });

    it('should clean up old offline data', async () => {
      const oldFiles = [
        { modificationTime: Date.now() - 31 * 24 * 60 * 60 * 1000 }, // 31 days old
      ];
      
      (FileSystem.readDirectoryAsync as jest.Mock).mockResolvedValue(['old-file.jpg']);
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue(oldFiles[0]);
      
      await offlineService.cleanupOldData();
      
      expect(FileSystem.deleteAsync).toHaveBeenCalledWith(
        expect.stringContaining('old-file.jpg')
      );
    });

    it('should respect storage limits', async () => {
      // Set storage limit to 100MB
      await offlineService.setStorageLimit(100 * 1024 * 1024);
      
      // Mock current usage at 95MB
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        size: 95 * 1024 * 1024,
      });
      
      // Try to download a 10MB file
      const canDownload = await offlineService.canDownloadFile(10 * 1024 * 1024);
      
      expect(canDownload).toBe(false);
    });
  });

  describe('Error Recovery', () => {
    it('should handle corrupted cache gracefully', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue('invalid json');
      
      const result = await offlineService.getCachedData('stories/1');
      
      expect(result).toBeNull();
    });

    it('should retry failed sync operations', async () => {
      let attempts = 0;
      (apiManager.request as jest.Mock).mockImplementation(() => {
        attempts++;
        if (attempts < 3) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({ data: 'success' });
      });
      
      await offlineService.syncWithRetry({
        method: 'POST',
        url: '/api/data',
      });
      
      expect(apiManager.request).toHaveBeenCalledTimes(3);
    });
  });
});