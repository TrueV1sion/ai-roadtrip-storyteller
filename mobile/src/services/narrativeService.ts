import { ApiClient } from './api/ApiClient';
import { logger } from '@/services/logger';
import {
  NarrativeGraphType,
  NarrativeStateType,
  CreateNarrativeRequest,
  NodeContentResponse,
  NarrativeProgressResponse
} from '../types/narrative';

class NarrativeService {
  /**
   * Creates a new interactive narrative based on location and preferences
   */
  async createNarrative(params: CreateNarrativeRequest): Promise<NarrativeGraphType> {
    try {
      return await ApiClient.post<NarrativeGraphType>('/interactive-narrative/create', params);
    } catch (error) {
      logger.error('Error creating narrative:', error);
      throw error;
    }
  }

  /**
   * Initializes a new state for an interactive narrative
   */
  async initializeState(narrativeId: string): Promise<NarrativeStateType> {
    try {
      return await ApiClient.post<NarrativeStateType>(
        `/interactive-narrative/initialize-state?narrative_id=${narrativeId}`
      );
    } catch (error) {
      logger.error('Error initializing narrative state:', error);
      throw error;
    }
  }

  /**
   * Makes a choice in an interactive narrative
   */
  async makeChoice(
    narrativeId: string,
    stateId: string,
    choiceId: string
  ): Promise<NarrativeStateType> {
    try {
      return await ApiClient.post<NarrativeStateType>('/interactive-narrative/make-choice', {
        narrative_id: narrativeId,
        state_id: stateId,
        choice_id: choiceId
      });
    } catch (error) {
      logger.error('Error making narrative choice:', error);
      throw error;
    }
  }

  /**
   * Gets the current node for a narrative state
   */
  async getCurrentNode(
    narrativeId: string,
    stateId: string
  ): Promise<NodeContentResponse> {
    try {
      return await ApiClient.get<NodeContentResponse>(
        `/interactive-narrative/current-node/${stateId}?narrative_id=${narrativeId}`
      );
    } catch (error) {
      logger.error('Error getting current narrative node:', error);
      throw error;
    }
  }

  /**
   * Gets personalized content for a specific node
   */
  async getNodeContent(
    narrativeId: string,
    stateId: string,
    nodeId: string
  ): Promise<NodeContentResponse> {
    try {
      return await ApiClient.post<NodeContentResponse>('/interactive-narrative/node-content', {
        narrative_id: narrativeId,
        state_id: stateId,
        node_id: nodeId
      });
    } catch (error) {
      logger.error('Error getting narrative node content:', error);
      throw error;
    }
  }

  /**
   * Gets progress information for a narrative state
   */
  async getProgress(
    narrativeId: string,
    stateId: string
  ): Promise<NarrativeProgressResponse> {
    try {
      return await ApiClient.get<NarrativeProgressResponse>(
        `/interactive-narrative/progress/${stateId}?narrative_id=${narrativeId}`
      );
    } catch (error) {
      logger.error('Error getting narrative progress:', error);
      throw error;
    }
  }

  /**
   * Gets all available narratives
   */
  async getNarratives(): Promise<NarrativeGraphType[]> {
    try {
      return await ApiClient.get<NarrativeGraphType[]>('/interactive-narrative/narratives');
    } catch (error) {
      logger.error('Error getting narratives:', error);
      throw error;
    }
  }

  /**
   * Gets all states owned by the current user
   */
  async getStates(): Promise<NarrativeStateType[]> {
    try {
      return await ApiClient.get<NarrativeStateType[]>('/interactive-narrative/states');
    } catch (error) {
      logger.error('Error getting narrative states:', error);
      throw error;
    }
  }

  /**
   * Creates a simple interactive narrative for a location
   */
  async createSimpleNarrative(
    locationName: string,
    locationType: string,
    locationDescription: string,
    theme: string = 'adventure'
  ): Promise<NarrativeGraphType> {
    const request: CreateNarrativeRequest = {
      location: {
        type: locationType,
        name: locationName,
        description: locationDescription
      },
      theme: theme,
      duration: 'medium',
      complexity: 1 // Simple complexity
    };

    return this.createNarrative(request);
  }
}

export const narrativeService = new NarrativeService();
export default narrativeService;