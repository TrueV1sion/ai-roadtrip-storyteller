/**
 * React Native Security Module Interface
 * Type definitions for native security module
 */

export interface RNSecurityModule {
  // iOS Jailbreak Detection
  checkJailbreak(): Promise<boolean>;
  canOpenURL(url: string): Promise<boolean>;
  isDebuggerAttached(): Promise<boolean>;
  
  // Android Root Detection
  checkPackages(packageName: string): Promise<boolean>;
  checkSuAccess(): Promise<boolean>;
  getBuildProperty(property: string): Promise<string | null>;
  getSELinuxStatus(): Promise<string>;
  isDebuggerConnected(): Promise<boolean>;
  
  // Common Security Features
  checkVPN(): Promise<boolean>;
  checkProxy(): Promise<boolean>;
  verifyCodeIntegrity(): Promise<boolean>;
  enableCertificatePinning(): Promise<void>;
  enableAntiDebugging(): Promise<void>;
  
  // Android Specific
  setScreenshotBlocking(enabled: boolean): Promise<void>;
  
  // iOS Specific
  enableBackgroundBlur(): Promise<void>;
}

// Native module documentation for implementation

/**
 * iOS Implementation (Objective-C/Swift)
 * 
 * File: ios/RNSecurityModule.m
 * 
 * @implementation RNSecurityModule
 * 
 * RCT_EXPORT_MODULE();
 * 
 * RCT_EXPORT_METHOD(checkJailbreak:(RCTPromiseResolveBlock)resolve
 *                   rejecter:(RCTPromiseRejectBlock)reject) {
 *   BOOL isJailbroken = NO;
 *   
 *   // Check for jailbreak files
 *   NSArray *paths = @[@"/Applications/Cydia.app",
 *                      @"/Library/MobileSubstrate/MobileSubstrate.dylib",
 *                      @"/bin/bash",
 *                      @"/usr/sbin/sshd",
 *                      @"/etc/apt",
 *                      @"/private/var/lib/apt/"];
 *   
 *   for (NSString *path in paths) {
 *     if ([[NSFileManager defaultManager] fileExistsAtPath:path]) {
 *       isJailbroken = YES;
 *       break;
 *     }
 *   }
 *   
 *   // Check if we can write outside sandbox
 *   if (!isJailbroken) {
 *     NSString *testPath = @"/private/test.txt";
 *     NSString *testString = @"test";
 *     NSError *error;
 *     
 *     [testString writeToFile:testPath atomically:YES encoding:NSUTF8StringEncoding error:&error];
 *     if (!error) {
 *       [[NSFileManager defaultManager] removeItemAtPath:testPath error:nil];
 *       isJailbroken = YES;
 *     }
 *   }
 *   
 *   // Check for suspicious URL schemes
 *   if (!isJailbroken) {
 *     NSArray *schemes = @[@"cydia://", @"sileo://", @"zbra://", @"undecimus://"];
 *     for (NSString *scheme in schemes) {
 *       if ([[UIApplication sharedApplication] canOpenURL:[NSURL URLWithString:scheme]]) {
 *         isJailbroken = YES;
 *         break;
 *       }
 *     }
 *   }
 *   
 *   resolve(@(isJailbroken));
 * }
 * 
 * RCT_EXPORT_METHOD(isDebuggerAttached:(RCTPromiseResolveBlock)resolve
 *                   rejecter:(RCTPromiseRejectBlock)reject) {
 *   #ifdef DEBUG
 *     resolve(@YES);
 *   #else
 *     // Check using sysctl
 *     int mib[4];
 *     struct kinfo_proc info;
 *     size_t size = sizeof(info);
 *     
 *     info.kp_proc.p_flag = 0;
 *     
 *     mib[0] = CTL_KERN;
 *     mib[1] = KERN_PROC;
 *     mib[2] = KERN_PROC_PID;
 *     mib[3] = getpid();
 *     
 *     sysctl(mib, 4, &info, &size, NULL, 0);
 *     
 *     resolve(@((info.kp_proc.p_flag & P_TRACED) != 0));
 *   #endif
 * }
 * 
 * @end
 */

/**
 * Android Implementation (Java/Kotlin)
 * 
 * File: android/src/main/java/com/roadtrip/RNSecurityModule.java
 * 
 * public class RNSecurityModule extends ReactContextBaseJavaModule {
 *   
 *   @Override
 *   public String getName() {
 *     return "RNSecurityModule";
 *   }
 *   
 *   @ReactMethod
 *   public void checkPackages(String packageName, Promise promise) {
 *     try {
 *       PackageManager pm = getReactApplicationContext().getPackageManager();
 *       pm.getPackageInfo(packageName, 0);
 *       promise.resolve(true);
 *     } catch (PackageManager.NameNotFoundException e) {
 *       promise.resolve(false);
 *     }
 *   }
 *   
 *   @ReactMethod
 *   public void checkSuAccess(Promise promise) {
 *     try {
 *       Runtime runtime = Runtime.getRuntime();
 *       Process process = runtime.exec("which su");
 *       BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
 *       String line = reader.readLine();
 *       promise.resolve(line != null);
 *     } catch (Exception e) {
 *       promise.resolve(false);
 *     }
 *   }
 *   
 *   @ReactMethod
 *   public void getBuildProperty(String property, Promise promise) {
 *     try {
 *       String value = getSystemProperty(property);
 *       promise.resolve(value);
 *     } catch (Exception e) {
 *       promise.resolve(null);
 *     }
 *   }
 *   
 *   @ReactMethod
 *   public void isDebuggerConnected(Promise promise) {
 *     promise.resolve(Debug.isDebuggerConnected());
 *   }
 *   
 *   @ReactMethod
 *   public void setScreenshotBlocking(boolean enabled, Promise promise) {
 *     Activity activity = getCurrentActivity();
 *     if (activity != null) {
 *       activity.runOnUiThread(() -> {
 *         if (enabled) {
 *           activity.getWindow().setFlags(
 *             WindowManager.LayoutParams.FLAG_SECURE,
 *             WindowManager.LayoutParams.FLAG_SECURE
 *           );
 *         } else {
 *           activity.getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
 *         }
 *         promise.resolve(null);
 *       });
 *     } else {
 *       promise.reject("NO_ACTIVITY", "No activity available");
 *     }
 *   }
 *   
 *   private String getSystemProperty(String key) {
 *     try {
 *       Class<?> systemProperties = Class.forName("android.os.SystemProperties");
 *       Method get = systemProperties.getMethod("get", String.class);
 *       return (String) get.invoke(null, key);
 *     } catch (Exception e) {
 *       return null;
 *     }
 *   }
 * }
 */