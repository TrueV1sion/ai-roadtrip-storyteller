/**
 * Utility functions for formatting various values for display
 */

/**
 * Formats a byte value into a human-readable string with appropriate units
 * @param bytes The number of bytes to format
 * @param decimals The number of decimal places to include (default: 2)
 * @returns A formatted string representation of the byte value
 */
export const formatBytes = (bytes: number, decimals: number = 2): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  // Format with the appropriate size unit and decimal places
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
};

/**
 * Formats a duration in seconds into a human-readable string
 * @param seconds The duration in seconds
 * @returns A formatted string representation of the duration
 */
export const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds} sec`;
  }
  
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min${minutes > 1 ? 's' : ''}`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  if (remainingMinutes === 0) {
    return `${hours} hr${hours > 1 ? 's' : ''}`;
  }
  
  return `${hours} hr${hours > 1 ? 's' : ''} ${remainingMinutes} min`;
};

/**
 * Formats a distance in meters into a human-readable string
 * @param meters The distance in meters
 * @param useMiles Whether to use miles instead of kilometers (default: true for US format)
 * @returns A formatted string representation of the distance
 */
export const formatDistance = (meters: number, useMiles: boolean = true): string => {
  if (useMiles) {
    const miles = meters / 1609.34;
    if (miles < 0.1) {
      // For very short distances, use feet
      const feet = meters * 3.28084;
      return `${Math.round(feet)} ft`;
    }
    return miles < 10 
      ? `${miles.toFixed(1)} mi` 
      : `${Math.round(miles)} mi`;
  } else {
    const km = meters / 1000;
    if (km < 0.1) {
      // For very short distances, use meters
      return `${Math.round(meters)} m`;
    }
    return km < 10 
      ? `${km.toFixed(1)} km` 
      : `${Math.round(km)} km`;
  }
};

/**
 * Formats a date to a short readable format
 * @param date The date to format
 * @returns A formatted string representation of the date
 */
export const formatShortDate = (date: Date): string => {
  const month = date.toLocaleString('default', { month: 'short' });
  const day = date.getDate();
  return `${month} ${day}`;
}; 