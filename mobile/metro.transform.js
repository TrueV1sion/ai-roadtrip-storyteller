/**
 * Custom Metro transformer with JavaScript obfuscation
 * Applies advanced obfuscation techniques to protect source code
 */

const upstreamTransformer = require('metro-react-native-babel-transformer');
const javascriptObfuscator = require('javascript-obfuscator');
const { createHash } = require('crypto');

// Obfuscation options for different security levels
const obfuscationOptions = {
  // High security obfuscation for production
  high: {
    compact: true,
    controlFlowFlattening: true,
    controlFlowFlatteningThreshold: 0.75,
    deadCodeInjection: true,
    deadCodeInjectionThreshold: 0.4,
    debugProtection: true,
    debugProtectionInterval: true,
    disableConsoleOutput: true,
    domainLock: [],  // Add your domains here if needed
    identifierNamesGenerator: 'hexadecimal',
    identifiersPrefix: 'rt',
    inputFileName: '',
    log: false,
    numbersToExpressions: true,
    renameGlobals: true,
    renameProperties: false,  // Can break React Native
    reservedNames: [
      // React Native reserved names
      'React', 'Component', 'render', 'props', 'state', 'setState',
      'componentDidMount', 'componentWillUnmount', 'constructor',
      'super', 'export', 'default', 'import', 'from', 'require',
      // React Navigation
      'navigation', 'navigate', 'goBack', 'push', 'pop',
      // Expo
      'expo', 'Constants', 'Location', 'Permissions',
    ],
    reservedStrings: [],
    rotateStringArray: true,
    seed: Date.now(),
    selfDefending: true,
    shuffleStringArray: true,
    simplify: true,
    sourceMap: false,
    sourceMapBaseUrl: '',
    sourceMapFileName: '',
    sourceMapMode: 'separate',
    splitStrings: true,
    splitStringsChunkLength: 10,
    stringArray: true,
    stringArrayCallsTransform: true,
    stringArrayCallsTransformThreshold: 0.75,
    stringArrayEncoding: ['base64', 'rc4'],
    stringArrayIndexShift: true,
    stringArrayRotate: true,
    stringArrayShuffle: true,
    stringArrayWrappersCount: 2,
    stringArrayWrappersChainedCalls: true,
    stringArrayWrappersParametersMaxCount: 4,
    stringArrayWrappersType: 'function',
    stringArrayThreshold: 0.75,
    target: 'browser',
    transformObjectKeys: true,
    unicodeEscapeSequence: false,
  },
  
  // Medium security for staging
  medium: {
    compact: true,
    controlFlowFlattening: true,
    controlFlowFlatteningThreshold: 0.5,
    deadCodeInjection: true,
    deadCodeInjectionThreshold: 0.2,
    debugProtection: false,
    disableConsoleOutput: true,
    identifierNamesGenerator: 'mangled',
    renameGlobals: true,
    rotateStringArray: true,
    selfDefending: false,
    shuffleStringArray: true,
    splitStrings: true,
    stringArray: true,
    stringArrayEncoding: ['base64'],
    stringArrayThreshold: 0.5,
    transformObjectKeys: true,
  },
  
  // Low security for development (minimal obfuscation)
  low: {
    compact: false,
    controlFlowFlattening: false,
    deadCodeInjection: false,
    debugProtection: false,
    disableConsoleOutput: false,
    renameGlobals: false,
    stringArray: false,
  },
};

// Files to skip obfuscation
const skipObfuscation = [
  'node_modules',
  '__tests__',
  '__mocks__',
  '.test.',
  '.spec.',
  'metro.config.js',
  'babel.config.js',
  'jest.config.js',
];

function shouldObfuscate(filename) {
  return !skipObfuscation.some(pattern => filename.includes(pattern));
}

function getObfuscationLevel() {
  if (process.env.NODE_ENV === 'production') {
    return 'high';
  } else if (process.env.NODE_ENV === 'staging') {
    return 'medium';
  }
  return 'low';
}

module.exports.transform = async ({ src, filename, options }) => {
  // First, apply the standard React Native transformations
  const result = await upstreamTransformer.transform({ src, filename, options });
  
  // Skip obfuscation in development or for excluded files
  if (process.env.NODE_ENV === 'development' || !shouldObfuscate(filename)) {
    return result;
  }
  
  try {
    // Get obfuscation level
    const level = getObfuscationLevel();
    const obfuscationConfig = obfuscationOptions[level];
    
    // Add file-specific seed for consistent obfuscation
    const fileHash = createHash('sha256').update(filename).digest('hex');
    obfuscationConfig.seed = parseInt(fileHash.substr(0, 8), 16);
    
    // Obfuscate the transformed code
    const obfuscationResult = javascriptObfuscator.obfuscate(
      result.code,
      obfuscationConfig
    );
    
    // Return the obfuscated code
    return {
      ...result,
      code: obfuscationResult.getObfuscatedCode(),
    };
  } catch (error) {
    console.error(`Obfuscation failed for ${filename}:`, error.message);
    // Return unobfuscated code on error to prevent build failures
    return result;
  }
};