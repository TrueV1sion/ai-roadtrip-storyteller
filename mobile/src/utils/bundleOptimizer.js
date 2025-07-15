/**
 * Bundle optimization configuration for React Native
 */
const path = require('path');

// Metro configuration for bundle optimization
module.exports = {
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true, // Enable inline requires for better performance
      },
    }),
    minifierPath: 'metro-minify-terser',
    minifierConfig: {
      // Terser options for better minification
      keep_fnames: false,
      mangle: {
        keep_fnames: false,
      },
      compress: {
        drop_console: true, // Remove console logs in production
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.warn', 'console.info'],
      },
      output: {
        ascii_only: true,
        quote_style: 3,
        wrap_iife: true,
      },
      sourceMap: {
        includeSources: false,
      },
      toplevel: false,
      module: false,
      keep_classnames: false,
      safari10: true,
    },
  },
  resolver: {
    // Asset extensions to bundle
    assetExts: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'mp3', 'mp4', 'ttf', 'otf', 'json'],
  },
  serializer: {
    getModulesRunBeforeMainModule: () => [
      // Preload performance critical modules
      require.resolve('./performancePolyfills.js'),
    ],
  },
};

// Webpack configuration for web builds
const webpackConfig = {
  mode: 'production',
  optimization: {
    usedExports: true,
    minimize: true,
    sideEffects: false,
    concatenateModules: true,
    runtimeChunk: 'single',
    splitChunks: {
      chunks: 'all',
      maxInitialRequests: 25,
      minSize: 20000,
      cacheGroups: {
        default: false,
        vendors: false,
        // Vendor code splitting
        vendor: {
          name: 'vendor',
          chunks: 'all',
          test: /[\\/]node_modules[\\/]/,
          priority: 20,
        },
        // Common components
        common: {
          name: 'common',
          minChunks: 2,
          chunks: 'all',
          priority: 10,
          reuseExistingChunk: true,
          enforce: true,
        },
        // React specific
        react: {
          test: /[\\/]node_modules[\\/](react|react-dom|react-native-web)[\\/]/,
          name: 'react',
          chunks: 'all',
          priority: 30,
        },
        // Navigation
        navigation: {
          test: /[\\/]node_modules[\\/](@react-navigation)[\\/]/,
          name: 'navigation',
          chunks: 'all',
          priority: 25,
        },
      },
    },
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-react', '@babel/preset-typescript'],
            plugins: [
              '@babel/plugin-syntax-dynamic-import',
              '@babel/plugin-proposal-class-properties',
              '@babel/plugin-transform-runtime',
              [
                'babel-plugin-transform-remove-console',
                {
                  exclude: ['error', 'warn'],
                },
              ],
            ],
          },
        },
      },
    ],
  },
  resolve: {
    alias: {
      // Optimize React Native for web
      'react-native$': 'react-native-web',
    },
    extensions: ['.web.js', '.js', '.web.ts', '.ts', '.web.tsx', '.tsx', '.json'],
  },
};

// Image optimization configuration
const imageOptimizationConfig = {
  quality: 85,
  progressive: true,
  optimizationLevel: 3,
  mozjpeg: {
    progressive: true,
    quality: 85,
  },
  pngquant: {
    quality: [0.65, 0.90],
    speed: 4,
  },
  gifsicle: {
    interlaced: false,
    optimizationLevel: 3,
  },
  webp: {
    quality: 85,
    method: 6,
  },
};

// Bundle analyzer configuration
const bundleAnalyzerConfig = {
  analyzerMode: 'static',
  reportFilename: 'bundle-report.html',
  openAnalyzer: false,
  generateStatsFile: true,
  statsFilename: 'bundle-stats.json',
};

module.exports = {
  webpackConfig,
  imageOptimizationConfig,
  bundleAnalyzerConfig,
};