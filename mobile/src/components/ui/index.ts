/**
 * UI Component Library Index
 * 
 * This exports all reusable UI components following the Bolt design patterns.
 * All components are built with:
 * - Dark theme first approach
 * - TypeScript for type safety
 * - Reanimated for smooth animations
 * - Accessibility support
 * - Consistent styling with Inter font
 */

export { Button } from './Button';
export type { ButtonVariant, ButtonSize } from './Button';

export { Card } from './Card';

export { Input } from './Input';

export { Typography } from './Typography';
export type { TypographyVariant } from './Typography';

export { PersonalityCard } from '../voice/PersonalityCard';
export { StoryCard } from '../story/StoryCard';

// Theme exports
export { colors } from '../../theme/colors';
export { spacing } from '../../theme/spacing';
export { typography } from '../../theme/typography';
export { shadows } from '../../theme/shadows';

// Utility exports
export { createStyles } from '../../utils/createStyles';
export { useTheme } from '../../hooks/useTheme';