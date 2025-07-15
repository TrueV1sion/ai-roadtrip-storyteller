#!/usr/bin/env python3
"""
Mobile Test Generator for React Native Road Trip App
Automatically generates comprehensive test suites for React Native components and screens
"""

import os
import re
import sys
import argparse
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json

class MobileTestGenerator:
    """Generates comprehensive test suites for React Native components"""
    
    def __init__(self, mobile_src_path: str):
        self.mobile_src_path = Path(mobile_src_path)
        self.component_patterns = {
            'screen': self._generate_screen_test,
            'component': self._generate_component_test,
            'service': self._generate_service_test,
            'hook': self._generate_hook_test,
            'context': self._generate_context_test,
        }
        
    def analyze_component(self, file_path: Path) -> Dict:
        """Analyze a component file to extract its structure"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        analysis = {
            'name': file_path.stem,
            'type': self._determine_component_type(file_path),
            'props': self._extract_props(content),
            'state': self._extract_state(content),
            'hooks': self._extract_hooks(content),
            'methods': self._extract_methods(content),
            'dependencies': self._extract_dependencies(content),
            'navigation': self._check_navigation(content),
            'api_calls': self._extract_api_calls(content),
            'async_operations': self._extract_async_operations(content),
        }
        
        return analysis
    
    def _determine_component_type(self, file_path: Path) -> str:
        """Determine the type of component based on file path and name"""
        if 'screens' in file_path.parts:
            return 'screen'
        elif 'services' in file_path.parts:
            return 'service'
        elif 'hooks' in file_path.parts:
            return 'hook'
        elif 'contexts' in file_path.parts:
            return 'context'
        else:
            return 'component'
    
    def _extract_props(self, content: str) -> List[str]:
        """Extract component props from TypeScript interface"""
        props = []
        # Look for interface Props or type Props
        props_match = re.search(r'(?:interface|type)\s+\w*Props\s*(?:=\s*)?\{([^}]+)\}', content, re.DOTALL)
        if props_match:
            props_content = props_match.group(1)
            # Extract property names
            prop_pattern = r'(\w+)\s*[?:]?\s*:'
            props = re.findall(prop_pattern, props_content)
        return props
    
    def _extract_state(self, content: str) -> List[str]:
        """Extract useState hooks"""
        state_pattern = r'const\s*\[(\w+),\s*set\w+\]\s*=\s*useState'
        return re.findall(state_pattern, content)
    
    def _extract_hooks(self, content: str) -> List[str]:
        """Extract React hooks used"""
        hook_pattern = r'use[A-Z]\w+(?:\(|<)'
        hooks = re.findall(hook_pattern, content)
        return list(set([h.rstrip('(<') for h in hooks]))
    
    def _extract_methods(self, content: str) -> List[str]:
        """Extract component methods"""
        # Look for const functions and regular functions
        const_func_pattern = r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'
        func_pattern = r'function\s+(\w+)\s*\([^)]*\)'
        
        const_funcs = re.findall(const_func_pattern, content)
        regular_funcs = re.findall(func_pattern, content)
        
        return list(set(const_funcs + regular_funcs))
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract import dependencies"""
        import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"\n]+)[\'"]'
        return re.findall(import_pattern, content)
    
    def _check_navigation(self, content: str) -> bool:
        """Check if component uses navigation"""
        return 'useNavigation' in content or 'navigation.' in content
    
    def _extract_api_calls(self, content: str) -> List[str]:
        """Extract API service calls"""
        api_pattern = r'(?:apiManager|authService|storyService|voiceService|locationService|rideshareService|drivingAssistantService|historicalService)\.(\w+)'
        return list(set(re.findall(api_pattern, content)))
    
    def _extract_async_operations(self, content: str) -> List[str]:
        """Extract async operations"""
        async_pattern = r'async\s+(?:function\s+)?(\w+)|const\s+(\w+)\s*=\s*async'
        matches = re.findall(async_pattern, content)
        return list(set([m[0] or m[1] for m in matches if m[0] or m[1]]))
    
    def generate_test(self, file_path: Path, force: bool = False) -> Optional[str]:
        """Generate test for a component file"""
        test_path = self._get_test_path(file_path)
        
        # Check if test already exists
        if test_path.exists() and not force:
            print(f"Test already exists: {test_path}")
            return None
            
        analysis = self.analyze_component(file_path)
        generator = self.component_patterns.get(analysis['type'], self._generate_component_test)
        
        test_content = generator(analysis)
        
        # Create test directory if needed
        test_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write test file
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
            
        print(f"Generated test: {test_path}")
        return str(test_path)
    
    def _get_test_path(self, file_path: Path) -> Path:
        """Get the test file path for a component"""
        parts = list(file_path.parts)
        # Insert __tests__ before filename
        filename = parts[-1]
        test_filename = filename.replace('.tsx', '.test.tsx').replace('.ts', '.test.ts')
        
        # Build test path
        test_parts = parts[:-1] + ['__tests__', test_filename]
        return Path(*test_parts)
    
    def _generate_screen_test(self, analysis: Dict) -> str:
        """Generate test for a screen component"""
        name = analysis['name']
        props = analysis['props']
        state = analysis['state']
        methods = analysis['methods']
        has_navigation = analysis['navigation']
        api_calls = analysis['api_calls']
        
        test_content = f'''import React from 'react';
import {{ render, fireEvent, waitFor, screen }} from '@testing-library/react-native';
import {{ NavigationContainer }} from '@react-navigation/native';
import {{ Provider }} from 'react-redux';
import {{ {name} }} from '../{name}';
import {{ mockStore }} from '../../test-utils/mockStore';
import {{ mockNavigation }} from '../../test-utils/mockNavigation';
'''

        if api_calls:
            test_content += f'''
// Mock API services
'''
            for api_call in set(api_calls):
                service = api_call.split('.')[0] if '.' in api_call else 'apiManager'
                test_content += f"jest.mock('@services/{service}');\n"

        test_content += f'''
describe('{name}', () => {{
  let store: any;
  let navigation: any;

  beforeEach(() => {{
    store = mockStore({{
      // Add initial state as needed
      user: {{ isAuthenticated: true }},
      app: {{ isLoading: false }},
    }});
    navigation = mockNavigation();
    jest.clearAllMocks();
  }});

  const renderScreen = (props = {{}}) => {{
    return render(
      <Provider store={{store}}>
        <NavigationContainer>
          <{name}
            navigation={{navigation}}
            route={{{{ params: {{}} }}}}
            {{...props}}
          />
        </NavigationContainer>
      </Provider>
    );
  }};

  describe('Rendering', () => {{
    it('should render without crashing', () => {{
      const {{ getByTestId }} = renderScreen();
      expect(getByTestId('{name.toLowerCase()}-container')).toBeTruthy();
    }});

    it('should display all required UI elements', () => {{
      renderScreen();
      // Add specific UI element checks based on screen
      expect(screen.getByText).toBeTruthy();
    }});

    it('should handle loading state', () => {{
      const {{ getByTestId }} = renderScreen();
      // Test loading indicators
    }});

    it('should handle error state', () => {{
      const {{ getByText }} = renderScreen();
      // Test error handling
    }});
  }});
'''

        if has_navigation:
            test_content += f'''
  describe('Navigation', () => {{
    it('should navigate correctly on user actions', async () => {{
      const {{ getByTestId }} = renderScreen();
      
      // Test navigation triggers
      const navigateButton = getByTestId('navigate-button');
      fireEvent.press(navigateButton);
      
      await waitFor(() => {{
        expect(navigation.navigate).toHaveBeenCalled();
      }});
    }});

    it('should handle back navigation', () => {{
      const {{ getByTestId }} = renderScreen();
      
      const backButton = getByTestId('back-button');
      fireEvent.press(backButton);
      
      expect(navigation.goBack).toHaveBeenCalled();
    }});
  }});
'''

        if state:
            test_content += f'''
  describe('State Management', () => {{
'''
            for state_var in state[:3]:  # Limit to first 3 state variables
                test_content += f'''    it('should update {state_var} state correctly', async () => {{
      const {{ getByTestId }} = renderScreen();
      
      // Test state updates
      const input = getByTestId('{state_var}-input');
      fireEvent.changeText(input, 'new value');
      
      await waitFor(() => {{
        expect(input.props.value).toBe('new value');
      }});
    }});

'''
            test_content += '  });\n'

        if api_calls:
            test_content += f'''
  describe('API Integration', () => {{
'''
            for api_call in api_calls[:3]:  # Limit to first 3 API calls
                test_content += f'''    it('should call {api_call} correctly', async () => {{
      const mockResponse = {{ data: 'test' }};
      const mockApi = require('@services/apiManager');
      mockApi.{api_call}.mockResolvedValue(mockResponse);
      
      renderScreen();
      
      await waitFor(() => {{
        expect(mockApi.{api_call}).toHaveBeenCalled();
      }});
    }});

'''
            test_content += '  });\n'

        test_content += f'''
  describe('User Interactions', () => {{
    it('should handle button presses', async () => {{
      const {{ getByTestId }} = renderScreen();
      
      const actionButton = getByTestId('action-button');
      fireEvent.press(actionButton);
      
      // Assert expected behavior
    }});

    it('should handle form submissions', async () => {{
      const {{ getByTestId }} = renderScreen();
      
      // Fill form
      const submitButton = getByTestId('submit-button');
      fireEvent.press(submitButton);
      
      await waitFor(() => {{
        // Assert form submission
      }});
    }});
  }});

  describe('Accessibility', () => {{
    it('should have proper accessibility labels', () => {{
      const {{ getByLabelText }} = renderScreen();
      
      // Test accessibility labels
      expect(getByLabelText).toBeTruthy();
    }});

    it('should support screen readers', () => {{
      const {{ getByTestId }} = renderScreen();
      
      const element = getByTestId('{name.lower()}-container');
      expect(element.props.accessible).toBe(true);
    }});
  }});

  describe('Performance', () => {{
    it('should not have unnecessary re-renders', () => {{
      const {{ rerender }} = renderScreen();
      
      // Test re-render optimization
      rerender(<{name} navigation={{navigation}} route={{{{ params: {{}} }}}} />);
      
      // Assert render count
    }});
  }});
}});
'''
        return test_content
    
    def _generate_component_test(self, analysis: Dict) -> str:
        """Generate test for a regular component"""
        name = analysis['name']
        props = analysis['props']
        
        test_content = f'''import React from 'react';
import {{ render, fireEvent, waitFor }} from '@testing-library/react-native';
import {{ {name} }} from '../{name}';

describe('{name}', () => {{
  const defaultProps = {{
'''
        for prop in props[:5]:  # Limit to first 5 props
            test_content += f'    {prop}: undefined,\n'
        
        test_content += f'''  }};

  const renderComponent = (props = {{}}) => {{
    return render(<{name} {{...defaultProps}} {{...props}} />);
  }};

  describe('Rendering', () => {{
    it('should render without crashing', () => {{
      const {{ getByTestId }} = renderComponent();
      expect(getByTestId('{name.lower()}-container')).toBeTruthy();
    }});

    it('should render with custom props', () => {{
      const customProps = {{
        // Add custom props
      }};
      const {{ getByText }} = renderComponent(customProps);
      // Assert custom rendering
    }});
  }});

  describe('Props', () => {{
'''
        for prop in props[:3]:
            test_content += f'''    it('should handle {prop} prop correctly', () => {{
      const {{ getByTestId }} = renderComponent({{ {prop}: 'test-value' }});
      // Assert prop handling
    }});

'''
        test_content += '''  });

  describe('User Interactions', () => {
    it('should handle press events', () => {
      const onPress = jest.fn();
      const { getByTestId } = renderComponent({ onPress });
      
      const button = getByTestId('component-button');
      fireEvent.press(button);
      
      expect(onPress).toHaveBeenCalled();
    });
  });

  describe('Styling', () => {
    it('should apply custom styles', () => {
      const customStyle = { backgroundColor: 'red' };
      const { getByTestId } = renderComponent({ style: customStyle });
      
      const container = getByTestId('{name.lower()}-container');
      expect(container.props.style).toContain(customStyle);
    });
  });
});
'''
        return test_content
    
    def _generate_service_test(self, analysis: Dict) -> str:
        """Generate test for a service"""
        name = analysis['name']
        methods = analysis['methods']
        async_ops = analysis['async_operations']
        
        test_content = f'''import {{ {name} }} from '../{name}';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {{ apiManager }} from '../apiManager';

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage');
jest.mock('../apiManager');

describe('{name}', () => {{
  beforeEach(() => {{
    jest.clearAllMocks();
    AsyncStorage.getItem.mockClear();
    AsyncStorage.setItem.mockClear();
  }});
'''

        for method in methods[:5]:  # Test first 5 methods
            is_async = method in async_ops
            test_content += f'''
  describe('{method}', () => {{
    it('should {method} successfully', {'async ' if is_async else ''}() => {{
      // Arrange
      const mockData = {{ test: 'data' }};
      {'const mockResponse = { data: mockData };' if is_async else ''}
      {f'apiManager.get.mockResolvedValue(mockResponse);' if is_async else ''}
      
      // Act
      {'const result = await' if is_async else 'const result ='} {name}.{method}();
      
      // Assert
      {'expect(result).toEqual(mockData);' if is_async else 'expect(result).toBeDefined();'}
    }});

    it('should handle errors in {method}', {'async ' if is_async else ''}() => {{
      // Arrange
      const mockError = new Error('Test error');
      {f'apiManager.get.mockRejectedValue(mockError);' if is_async else ''}
      
      // Act & Assert
      {'await expect(' if is_async else 'expect(() => '}{name}.{method}()){'').rejects.toThrow(mockError);' if is_async else '.toThrow();'}
    }});
  }});
'''

        test_content += '''
  describe('Caching', () => {
    it('should cache responses', async () => {
      const mockData = { cached: true };
      AsyncStorage.getItem.mockResolvedValue(null);
      apiManager.get.mockResolvedValue({ data: mockData });
      
      // First call
      await {name}.getData();
      
      // Second call should use cache
      await {name}.getData();
      
      expect(apiManager.get).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const networkError = new Error('Network error');
      apiManager.get.mockRejectedValue(networkError);
      
      const result = await {name}.getData();
      
      expect(result).toBeNull();
    });
  });
});
'''
        return test_content
    
    def _generate_hook_test(self, analysis: Dict) -> str:
        """Generate test for a custom hook"""
        name = analysis['name']
        
        test_content = f'''import {{ renderHook, act }} from '@testing-library/react-hooks';
import {{ {name} }} from '../{name}';

describe('{name}', () => {{
  it('should initialize with default values', () => {{
    const {{ result }} = renderHook(() => {name}());
    
    // Assert initial state
    expect(result.current).toBeDefined();
  }});

  it('should update state correctly', () => {{
    const {{ result }} = renderHook(() => {name}());
    
    act(() => {{
      // Trigger state update
    }});
    
    // Assert updated state
  }});

  it('should handle cleanup on unmount', () => {{
    const {{ unmount }} = renderHook(() => {name}());
    
    unmount();
    
    // Assert cleanup
  }});

  it('should memoize expensive computations', () => {{
    const {{ result, rerender }} = renderHook(() => {name}());
    
    const firstResult = result.current;
    rerender();
    const secondResult = result.current;
    
    // Assert memoization
    expect(firstResult).toBe(secondResult);
  }});
}});
'''
        return test_content
    
    def _generate_context_test(self, analysis: Dict) -> str:
        """Generate test for a context provider"""
        name = analysis['name']
        
        test_content = f'''import React from 'react';
import {{ render, act }} from '@testing-library/react-native';
import {{ {name}, {name.replace('Context', 'Provider')}, use{name.replace('Context', '')} }} from '../{name}';

describe('{name}', () => {{
  const TestComponent = () => {{
    const context = use{name.replace('Context', '')}();
    return <Text testID="context-value">{{JSON.stringify(context)}}</Text>;
  }};

  it('should provide context values', () => {{
    const {{ getByTestId }} = render(
      <{name.replace('Context', 'Provider')}>
        <TestComponent />
      </{name.replace('Context', 'Provider')}>
    );
    
    const contextValue = getByTestId('context-value');
    expect(contextValue).toBeTruthy();
  }});

  it('should update context values', () => {{
    const {{ getByTestId }} = render(
      <{name.replace('Context', 'Provider')}>
        <TestComponent />
      </{name.replace('Context', 'Provider')}>
    );
    
    act(() => {{
      // Trigger context update
    }});
    
    // Assert updated values
  }});

  it('should throw error when used outside provider', () => {{
    // Suppress console.error for this test
    const spy = jest.spyOn(console, 'error').mockImplementation();
    
    expect(() => {{
      render(<TestComponent />);
    }}).toThrow();
    
    spy.mockRestore();
  }});
}});
'''
        return test_content
    
    def generate_missing_tests(self, dry_run: bool = False) -> List[str]:
        """Generate all missing tests in the codebase"""
        generated_tests = []
        
        # Find all testable files
        patterns = ['**/*.tsx', '**/*.ts']
        exclude_patterns = ['**/*.test.*', '**/*.spec.*', '**/node_modules/**', '**/__tests__/**']
        
        for pattern in patterns:
            for file_path in self.mobile_src_path.glob(pattern):
                # Skip if in exclude patterns
                if any(file_path.match(exclude) for exclude in exclude_patterns):
                    continue
                    
                # Skip index files and type definitions
                if file_path.name in ['index.ts', 'index.tsx'] or file_path.suffix == '.d.ts':
                    continue
                
                test_path = self._get_test_path(file_path)
                if not test_path.exists():
                    print(f"Missing test for: {file_path}")
                    if not dry_run:
                        test_file = self.generate_test(file_path)
                        if test_file:
                            generated_tests.append(test_file)
                        
        return generated_tests
    
    def generate_test_utils(self):
        """Generate common test utilities"""
        utils_dir = self.mobile_src_path / 'test-utils'
        utils_dir.mkdir(exist_ok=True)
        
        # Mock Store utility
        mock_store_content = '''import configureStore from 'redux-mock-store';
import thunk from 'redux-thunk';

const middlewares = [thunk];
const mockStoreCreator = configureStore(middlewares);

export const mockStore = (initialState = {}) => {
  return mockStoreCreator({
    user: {
      isAuthenticated: false,
      profile: null,
      ...initialState.user,
    },
    app: {
      isLoading: false,
      error: null,
      ...initialState.app,
    },
    story: {
      currentStory: null,
      isPlaying: false,
      ...initialState.story,
    },
    voice: {
      personality: 'morgan-freeman',
      isListening: false,
      ...initialState.voice,
    },
    navigation: {
      currentRoute: null,
      destination: null,
      ...initialState.navigation,
    },
    ...initialState,
  });
};
'''
        with open(utils_dir / 'mockStore.ts', 'w') as f:
            f.write(mock_store_content)
        
        # Mock Navigation utility
        mock_navigation_content = '''export const mockNavigation = () => ({
  navigate: jest.fn(),
  goBack: jest.fn(),
  push: jest.fn(),
  pop: jest.fn(),
  popToTop: jest.fn(),
  replace: jest.fn(),
  reset: jest.fn(),
  setParams: jest.fn(),
  dispatch: jest.fn(),
  setOptions: jest.fn(),
  addListener: jest.fn(),
  removeListener: jest.fn(),
  canGoBack: jest.fn(() => true),
  getParent: jest.fn(),
  getState: jest.fn(() => ({
    routes: [],
    index: 0,
  })),
});
'''
        with open(utils_dir / 'mockNavigation.ts', 'w') as f:
            f.write(mock_navigation_content)
        
        # Test Helpers
        test_helpers_content = '''import { ReactTestInstance } from 'react-test-renderer';
import { waitFor } from '@testing-library/react-native';

export const findByTestId = (
  component: ReactTestInstance,
  testId: string
): ReactTestInstance | null => {
  try {
    return component.findByProps({ testID: testId });
  } catch {
    return null;
  }
};

export const waitForElement = async (
  fn: () => any,
  timeout = 5000
): Promise<any> => {
  return waitFor(fn, { timeout });
};

export const mockAsyncStorage = () => {
  const store: { [key: string]: string } = {};
  
  return {
    getItem: jest.fn((key) => Promise.resolve(store[key] || null)),
    setItem: jest.fn((key, value) => {
      store[key] = value;
      return Promise.resolve();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
      return Promise.resolve();
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach((key) => delete store[key]);
      return Promise.resolve();
    }),
    getAllKeys: jest.fn(() => Promise.resolve(Object.keys(store))),
  };
};

export const mockGeolocation = () => ({
  getCurrentPosition: jest.fn((success) =>
    success({
      coords: {
        latitude: 37.7749,
        longitude: -122.4194,
        accuracy: 10,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
      },
      timestamp: Date.now(),
    })
  ),
  watchPosition: jest.fn(),
  clearWatch: jest.fn(),
  stopObserving: jest.fn(),
});
'''
        with open(utils_dir / 'testHelpers.ts', 'w') as f:
            f.write(test_helpers_content)
        
        print(f"Generated test utilities in {utils_dir}")


def main():
    parser = argparse.ArgumentParser(description='Generate tests for React Native components')
    parser.add_argument('--path', help='Path to mobile src directory', 
                       default='/mnt/c/users/jared/onedrive/desktop/roadtrip/mobile/src')
    parser.add_argument('--component', help='Generate test for specific component')
    parser.add_argument('--all', action='store_true', help='Generate all missing tests')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated')
    parser.add_argument('--force', action='store_true', help='Overwrite existing tests')
    parser.add_argument('--utils', action='store_true', help='Generate test utilities')
    
    args = parser.parse_args()
    
    generator = MobileTestGenerator(args.path)
    
    if args.utils:
        generator.generate_test_utils()
    elif args.component:
        component_path = Path(args.component)
        if not component_path.is_absolute():
            component_path = Path(args.path) / component_path
        generator.generate_test(component_path, force=args.force)
    elif args.all:
        tests = generator.generate_missing_tests(dry_run=args.dry_run)
        print(f"\nGenerated {len(tests)} test files")
    else:
        print("Please specify --component, --all, or --utils")
        parser.print_help()


if __name__ == '__main__':
    main()