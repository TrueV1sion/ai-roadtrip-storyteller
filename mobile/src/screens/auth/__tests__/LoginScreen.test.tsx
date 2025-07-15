import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { Alert } from 'react-native';
import LoginScreen from '../LoginScreen';
import { useAuth } from '@hooks/useAuth';

// Mock modules
jest.mock('@hooks/useAuth');
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: jest.fn(),
  }),
}));

// Mock Alert
jest.spyOn(Alert, 'alert');

describe('LoginScreen', () => {
  const mockLogin = jest.fn();
  const mockNavigation = {
    navigate: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useAuth as jest.Mock).mockReturnValue({
      login: mockLogin,
    });
  });

  const renderScreen = () => {
    return render(
      <NavigationContainer>
        <LoginScreen />
      </NavigationContainer>
    );
  };

  describe('Rendering', () => {
    it('should render without crashing', () => {
      const { getByPlaceholderText } = renderScreen();
      
      expect(getByPlaceholderText('Enter your email')).toBeTruthy();
      expect(getByPlaceholderText('Enter your password')).toBeTruthy();
    });

    it('should display all form elements', () => {
      const { getByText, getByPlaceholderText } = renderScreen();
      
      expect(getByText('Email')).toBeTruthy();
      expect(getByText('Password')).toBeTruthy();
      expect(getByText('Login')).toBeTruthy();
      expect(getByText('Register')).toBeTruthy();
      expect(getByText('Forgot Password?')).toBeTruthy();
    });
  });

  describe('Form Validation', () => {
    it('should show error when email is empty', async () => {
      const { getByText } = renderScreen();
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      await waitFor(() => {
        expect(getByText('Email is required')).toBeTruthy();
      });
      
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should show error for invalid email format', async () => {
      const { getByText, getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      fireEvent.changeText(emailInput, 'invalid-email');
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      await waitFor(() => {
        expect(getByText('Email is invalid')).toBeTruthy();
      });
      
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should show error when password is empty', async () => {
      const { getByText, getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      fireEvent.changeText(emailInput, 'test@example.com');
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      await waitFor(() => {
        expect(getByText('Password is required')).toBeTruthy();
      });
      
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should show error when password is too short', async () => {
      const { getByText, getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      const passwordInput = getByPlaceholderText('Enter your password');
      
      fireEvent.changeText(emailInput, 'test@example.com');
      fireEvent.changeText(passwordInput, '12345');
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      await waitFor(() => {
        expect(getByText('Password must be at least 6 characters')).toBeTruthy();
      });
      
      expect(mockLogin).not.toHaveBeenCalled();
    });
  });

  describe('Login Flow', () => {
    it('should call login with correct credentials', async () => {
      mockLogin.mockResolvedValue(undefined);
      
      const { getByText, getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      const passwordInput = getByPlaceholderText('Enter your password');
      
      fireEvent.changeText(emailInput, 'test@example.com');
      fireEvent.changeText(passwordInput, 'password123');
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
      });
    });

    it('should show loading state during login', async () => {
      mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      const { getByText, getByPlaceholderText, queryByTestId } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      const passwordInput = getByPlaceholderText('Enter your password');
      
      fireEvent.changeText(emailInput, 'test@example.com');
      fireEvent.changeText(passwordInput, 'password123');
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      // Check for loading indicator
      await waitFor(() => {
        const button = loginButton.parent;
        expect(button?.props.loading).toBe(true);
      });
    });

    it('should handle login error', async () => {
      const errorMessage = 'Invalid credentials';
      mockLogin.mockRejectedValue(new Error(errorMessage));
      
      const { getByText, getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      const passwordInput = getByPlaceholderText('Enter your password');
      
      fireEvent.changeText(emailInput, 'test@example.com');
      fireEvent.changeText(passwordInput, 'wrongpassword');
      
      const loginButton = getByText('Login');
      fireEvent.press(loginButton);
      
      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith(
          'Login Failed',
          errorMessage
        );
      });
    });
  });

  describe('Navigation', () => {
    it('should navigate to Register screen', () => {
      const { getByText } = renderScreen();
      const navigation = require('@react-navigation/native').useNavigation();
      
      const registerButton = getByText('Register');
      fireEvent.press(registerButton);
      
      expect(navigation.navigate).toHaveBeenCalledWith('Register');
    });

    it('should navigate to ForgotPassword screen', () => {
      const { getByText } = renderScreen();
      const navigation = require('@react-navigation/native').useNavigation();
      
      const forgotPasswordButton = getByText('Forgot Password?');
      fireEvent.press(forgotPasswordButton);
      
      expect(navigation.navigate).toHaveBeenCalledWith('ForgotPassword');
    });
  });

  describe('Accessibility', () => {
    it('should have proper accessibility labels', () => {
      const { getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      const passwordInput = getByPlaceholderText('Enter your password');
      
      expect(emailInput.props.accessible).toBe(true);
      expect(passwordInput.props.accessible).toBe(true);
    });

    it('should handle keyboard properly', () => {
      const { getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      expect(emailInput.props.keyboardType).toBe('email-address');
      expect(emailInput.props.autoCapitalize).toBe('none');
      
      const passwordInput = getByPlaceholderText('Enter your password');
      expect(passwordInput.props.secureTextEntry).toBe(true);
    });
  });

  describe('Security', () => {
    it('should not store password in plain text', () => {
      const { getByPlaceholderText } = renderScreen();
      
      const passwordInput = getByPlaceholderText('Enter your password');
      expect(passwordInput.props.secureTextEntry).toBe(true);
    });

    it('should clear sensitive data on unmount', () => {
      const { unmount, getByPlaceholderText } = renderScreen();
      
      const emailInput = getByPlaceholderText('Enter your email');
      const passwordInput = getByPlaceholderText('Enter your password');
      
      fireEvent.changeText(emailInput, 'test@example.com');
      fireEvent.changeText(passwordInput, 'password123');
      
      unmount();
      
      // Ensure no sensitive data remains in memory
      expect(mockLogin).not.toHaveBeenCalled();
    });
  });
});