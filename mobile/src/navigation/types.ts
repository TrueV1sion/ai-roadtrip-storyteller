import { NavigatorScreenParams } from '@react-navigation/native';

export type RootStackParamList = {
  Auth: undefined;
  Main: NavigatorScreenParams<MainTabParamList>;
  ImmersiveExperience: undefined;
  DrivingMode: { destination?: string };
  VoiceBooking: { venue?: string; type?: 'restaurant' | 'attraction' | 'hotel'; isDriving?: boolean };
  NavigationView: { destination: string };
};

export type MainTabParamList = {
  Home: undefined;
  Trip: undefined;
  Stories: undefined;
  Profile: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};

export type HomeStackParamList = {
  HomeScreen: undefined;
  StoryDetail: { storyId: string };
  TripPlanner: undefined;
  ImmersiveExperience: undefined;
  DrivingMode: { destination?: string };
};

export type TripStackParamList = {
  ActiveTrip: undefined;
  TripDetails: { tripId: string };
  Navigation: { tripId: string };
  Games: undefined;
  VoiceNavigation: undefined;
  DrivingMode: { destination?: string };
};

export type StoriesStackParamList = {
  StoriesList: undefined;
  StoryDetail: { storyId: string };
  SavedTrips: undefined;
};

export type ProfileStackParamList = {
  ProfileScreen: undefined;
  Settings: undefined;
  Preferences: undefined;
  About: undefined;
}; 