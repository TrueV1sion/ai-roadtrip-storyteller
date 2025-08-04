import React from 'react';
import {
  Text,
  StyleSheet,
  TextStyle,
  TextProps as RNTextProps,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSpring,
} from 'react-native-reanimated';

export type TypographyVariant = 
  | 'h1'
  | 'h2'
  | 'h3'
  | 'h4'
  | 'h5'
  | 'h6'
  | 'subtitle1'
  | 'subtitle2'
  | 'body1'
  | 'body2'
  | 'caption'
  | 'overline'
  | 'button';

interface TypographyProps extends RNTextProps {
  variant?: TypographyVariant;
  color?: string;
  align?: 'left' | 'center' | 'right' | 'justify';
  weight?: 'regular' | 'medium' | 'semibold' | 'bold';
  italic?: boolean;
  underline?: boolean;
  strikethrough?: boolean;
  uppercase?: boolean;
  lowercase?: boolean;
  capitalize?: boolean;
  gutterBottom?: boolean;
  noWrap?: boolean;
  animate?: boolean;
  animationType?: 'fadeIn' | 'slideIn' | 'scale';
  style?: TextStyle;
  children: React.ReactNode;
}

const AnimatedText = Animated.createAnimatedComponent(Text);

export const Typography: React.FC<TypographyProps> = ({
  variant = 'body1',
  color = '#ffffff',
  align = 'left',
  weight,
  italic = false,
  underline = false,
  strikethrough = false,
  uppercase = false,
  lowercase = false,
  capitalize = false,
  gutterBottom = false,
  noWrap = false,
  animate = false,
  animationType = 'fadeIn',
  style,
  children,
  ...textProps
}) => {
  const opacity = useSharedValue(animate ? 0 : 1);
  const translateY = useSharedValue(animate && animationType === 'slideIn' ? 20 : 0);
  const scale = useSharedValue(animate && animationType === 'scale' ? 0.8 : 1);

  React.useEffect(() => {
    if (animate) {
      opacity.value = withTiming(1, { duration: 500 });
      
      if (animationType === 'slideIn') {
        translateY.value = withSpring(0, { damping: 15, stiffness: 100 });
      } else if (animationType === 'scale') {
        scale.value = withSpring(1, { damping: 15, stiffness: 100 });
      }
    }
  }, [animate, animationType]);

  const animatedStyle = useAnimatedStyle(() => {
    return {
      opacity: opacity.value,
      transform: [
        { translateY: translateY.value },
        { scale: scale.value },
      ],
    };
  });

  const getTextTransform = () => {
    if (uppercase) return 'uppercase';
    if (lowercase) return 'lowercase';
    if (capitalize) return 'capitalize';
    return 'none';
  };

  const textStyle: TextStyle[] = [
    styles[variant],
    weight && fontWeights[weight],
    {
      color,
      textAlign: align,
      fontStyle: italic ? 'italic' : 'normal',
      textDecorationLine: underline
        ? strikethrough
          ? 'underline line-through'
          : 'underline'
        : strikethrough
        ? 'line-through'
        : 'none',
      textTransform: getTextTransform(),
    },
    gutterBottom && styles.gutterBottom,
    noWrap && styles.noWrap,
    style,
  ];

  if (animate) {
    return (
      <AnimatedText
        {...textProps}
        style={[textStyle, animatedStyle]}
        numberOfLines={noWrap ? 1 : undefined}
        ellipsizeMode={noWrap ? 'tail' : undefined}
      >
        {children}
      </AnimatedText>
    );
  }

  return (
    <Text
      {...textProps}
      style={textStyle}
      numberOfLines={noWrap ? 1 : undefined}
      ellipsizeMode={noWrap ? 'tail' : undefined}
    >
      {children}
    </Text>
  );
};

const fontWeights = StyleSheet.create({
  regular: {
    fontFamily: 'Inter-Regular',
  },
  medium: {
    fontFamily: 'Inter-Medium',
  },
  semibold: {
    fontFamily: 'Inter-SemiBold',
  },
  bold: {
    fontFamily: 'Inter-Bold',
  },
});

const styles = StyleSheet.create({
  h1: {
    fontSize: 48,
    fontFamily: 'Inter-Bold',
    lineHeight: 56,
    letterSpacing: -1.5,
  },
  h2: {
    fontSize: 40,
    fontFamily: 'Inter-Bold',
    lineHeight: 48,
    letterSpacing: -0.5,
  },
  h3: {
    fontSize: 32,
    fontFamily: 'Inter-Bold',
    lineHeight: 40,
    letterSpacing: 0,
  },
  h4: {
    fontSize: 28,
    fontFamily: 'Inter-SemiBold',
    lineHeight: 36,
    letterSpacing: 0.25,
  },
  h5: {
    fontSize: 24,
    fontFamily: 'Inter-SemiBold',
    lineHeight: 32,
    letterSpacing: 0,
  },
  h6: {
    fontSize: 20,
    fontFamily: 'Inter-SemiBold',
    lineHeight: 28,
    letterSpacing: 0.15,
  },
  subtitle1: {
    fontSize: 18,
    fontFamily: 'Inter-Medium',
    lineHeight: 26,
    letterSpacing: 0.15,
  },
  subtitle2: {
    fontSize: 16,
    fontFamily: 'Inter-Medium',
    lineHeight: 24,
    letterSpacing: 0.1,
  },
  body1: {
    fontSize: 16,
    fontFamily: 'Inter-Regular',
    lineHeight: 24,
    letterSpacing: 0.5,
  },
  body2: {
    fontSize: 14,
    fontFamily: 'Inter-Regular',
    lineHeight: 20,
    letterSpacing: 0.25,
  },
  caption: {
    fontSize: 12,
    fontFamily: 'Inter-Regular',
    lineHeight: 16,
    letterSpacing: 0.4,
  },
  overline: {
    fontSize: 10,
    fontFamily: 'Inter-Medium',
    lineHeight: 16,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  button: {
    fontSize: 16,
    fontFamily: 'Inter-SemiBold',
    lineHeight: 24,
    letterSpacing: 1.25,
  },
  gutterBottom: {
    marginBottom: 16,
  },
  noWrap: {
    // React Native handles this via numberOfLines prop
  },
});

export default Typography;