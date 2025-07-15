/**
 * Types for the interactive narrative system
 */

// Basic types
export interface NarrativeChoiceType {
  id: string;
  text: string;
  description: string;
  consequences?: Record<string, any>;
}

export interface NarrativeNodeType {
  id: string;
  title: string;
  content: string;
  image_prompt?: string;
  audio_prompt?: string;
  choices: NarrativeChoiceType[];
  metadata?: Record<string, any>;
}

export interface NarrativeStateType {
  id: string;
  current_node_id: string;
  visited_nodes: string[];
  inventory: Record<string, any>;
  character_traits: Record<string, number>;
  story_variables: Record<string, any>;
}

export interface StoryMetadataType {
  id: string;
  title: string;
  description: string;
  theme: string;
  location_type: string;
  duration: string;
  created_at: string;
  tags: string[];
}

export interface NarrativeGraphType {
  id: string;
  metadata: StoryMetadataType;
  nodes: Record<string, NarrativeNodeType>;
  initial_node_id: string;
}

// Request/Response types

export interface CreateNarrativeRequest {
  location: {
    type: string;
    name: string;
    description: string;
    attractions?: string[];
    [key: string]: any;
  };
  theme: string;
  duration?: string;
  complexity?: number;
}

export interface NodeContentResponse {
  node: NarrativeNodeType;
  personalized_content: Record<string, any>;
  available_choices: NarrativeChoiceType[];
}

export interface NarrativeProgressResponse {
  narrative_id: string;
  state: NarrativeStateType;
  current_node?: NodeContentResponse;
  completion_percentage: number;
  choices_made: number;
}

// Optional inventory item object for stronger typing
export interface InventoryItem {
  id: string;
  name: string;
  description: string;
  image_url?: string;
  quantity: number;
  effects?: Record<string, any>;
}

// Character trait types for stronger typing
export type CharacterTraitType = 
  | 'courage'
  | 'wisdom'
  | 'kindness'
  | 'curiosity'
  | 'leadership'
  | 'resourcefulness'
  | string;

// Story theme types for stronger typing
export type StoryThemeType = 
  | 'historical'
  | 'mystery'
  | 'adventure'
  | 'nature'
  | 'cultural'
  | 'fantasy'
  | 'sci-fi'
  | string;