/**
 * AR Services Export
 */

export { arCameraService } from './ARCameraService';
export { arLandmarkService } from './ARLandmarkService';
export { arOverlayRenderer } from './AROverlayRenderer';
export { arPhotoCaptureService } from './ARPhotoCapture';
export { arGameEngine } from './ARGameEngine';

export type {
  ARLandmark,
  LandmarkCluster,
} from './ARLandmarkService';

export type {
  AROverlay,
  OverlayTheme,
  RenderConfig,
} from './AROverlayRenderer';

export type {
  ARPhotoMetadata,
  ARPhotoFrame,
  PhotoCaptureResult,
} from './ARPhotoCapture';

export type {
  ARGame,
  ARGameSession,
  ARGameObjective,
} from './ARGameEngine';
