import React, { useState } from 'react';
import { StyleSheet, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { SafeArea, ScrollContainer, Input, Button } from '@components/index';
import { useAuth } from '@hooks/useAuth';
import { AuthStackParamList } from '@navigation/types';
import { THEME } from '@/config';

type LoginScreenNavigationProp = NativeStackNavigationProp<
  AuthStackParamList,
  'Login'
>;

export default function LoginScreen() {
  const navigation = useNavigation<LoginScreenNavigationProp>();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({
    email: '',
    password: '',
  });

  const validateForm = () => {
    const newErrors = {
      email: '',
      password: '',
    };

    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Email is invalid';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    setErrors(newErrors);
    return !newErrors.email && !newErrors.password;
  };

  const handleLogin = async () => {
    if (!validateForm()) return;

    setLoading(true);
    try {
      await login(email, password);
    } catch (error) {
      Alert.alert(
        'Login Failed',
        error instanceof Error ? error.message : 'Please try again later'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeArea>
      <ScrollContainer
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Input
          label="Email"
          value={email}
          onChangeText={setEmail}
          placeholder="Enter your email"
          keyboardType="email-address"
          autoCapitalize="none"
          error={errors.email}
          required
        />
        <Input
          label="Password"
          value={password}
          onChangeText={setPassword}
          placeholder="Enter your password"
          secureTextEntry
          error={errors.password}
          required
        />
        <Button
          title="Login"
          onPress={handleLogin}
          loading={loading}
          style={styles.button}
          fullWidth
        />
        <Button
          title="Register"
          onPress={() => navigation.navigate('Register')}
          variant="outline"
          style={styles.button}
          fullWidth
        />
        <Button
          title="Forgot Password?"
          onPress={() => navigation.navigate('ForgotPassword')}
          variant="secondary"
          style={styles.button}
          fullWidth
        />
      </ScrollContainer>
    </SafeArea>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: THEME.spacing.lg,
    justifyContent: 'center',
    minHeight: '100%',
  },
  button: {
    marginTop: THEME.spacing.md,
  },
}); 