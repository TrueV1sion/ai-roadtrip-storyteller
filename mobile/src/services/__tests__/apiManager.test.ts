import axios from 'axios';
import apiManager from '../api/apiManager';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('ApiManager', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('get', () => {
    it('makes GET request with correct URL', async () => {
      const mockData = { data: 'test' };
      mockedAxios.get.mockResolvedValueOnce({ data: mockData });

      const result = await apiManager.get('/test-endpoint');
      
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/test-endpoint'),
        expect.any(Object)
      );
      expect(result).toEqual(mockData);
    });

    it('includes auth token in headers', async () => {
      const mockData = { data: 'test' };
      mockedAxios.get.mockResolvedValueOnce({ data: mockData });
      
      // Mock token storage
      jest.spyOn(require('@react-native-async-storage/async-storage'), 'getItem')
        .mockResolvedValueOnce('test-token');

      await apiManager.get('/test-endpoint');
      
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token'
          })
        })
      );
    });

    it('handles network errors', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));

      await expect(apiManager.get('/test-endpoint')).rejects.toThrow('Network error');
    });
  });

  describe('post', () => {
    it('makes POST request with data', async () => {
      const postData = { name: 'test' };
      const mockResponse = { id: 1, ...postData };
      mockedAxios.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await apiManager.post('/test-endpoint', postData);
      
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/test-endpoint'),
        postData,
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });

    it('handles validation errors', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: { error: 'Validation failed' }
        }
      };
      mockedAxios.post.mockRejectedValueOnce(errorResponse);

      await expect(apiManager.post('/test-endpoint', {})).rejects.toMatchObject({
        response: expect.objectContaining({ status: 400 })
      });
    });
  });

  describe('put', () => {
    it('makes PUT request with data', async () => {
      const putData = { name: 'updated' };
      const mockResponse = { id: 1, ...putData };
      mockedAxios.put.mockResolvedValueOnce({ data: mockResponse });

      const result = await apiManager.put('/test-endpoint/1', putData);
      
      expect(mockedAxios.put).toHaveBeenCalledWith(
        expect.stringContaining('/test-endpoint/1'),
        putData,
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('delete', () => {
    it('makes DELETE request', async () => {
      mockedAxios.delete.mockResolvedValueOnce({ data: { success: true } });

      const result = await apiManager.delete('/test-endpoint/1');
      
      expect(mockedAxios.delete).toHaveBeenCalledWith(
        expect.stringContaining('/test-endpoint/1'),
        expect.any(Object)
      );
      expect(result).toEqual({ success: true });
    });
  });

  describe('error handling', () => {
    it('retries failed requests', async () => {
      mockedAxios.get
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ data: { success: true } });

      const result = await apiManager.get('/test-endpoint');
      
      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      expect(result).toEqual({ success: true });
    });

    it('handles timeout errors', async () => {
      const timeoutError = new Error('timeout');
      (timeoutError as any).code = 'ECONNABORTED';
      mockedAxios.get.mockRejectedValueOnce(timeoutError);

      await expect(apiManager.get('/test-endpoint')).rejects.toThrow('timeout');
    });

    it('handles 401 unauthorized errors', async () => {
      const unauthorizedError = {
        response: { status: 401 }
      };
      mockedAxios.get.mockRejectedValueOnce(unauthorizedError);

      await expect(apiManager.get('/test-endpoint')).rejects.toMatchObject({
        response: { status: 401 }
      });
    });
  });
});