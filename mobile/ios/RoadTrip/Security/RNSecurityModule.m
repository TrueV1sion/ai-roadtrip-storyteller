/**
 * iOS Security Module Implementation
 * Certificate pinning and jailbreak detection for iOS
 */

#import <React/RCTBridgeModule.h>
#import <React/RCTEventEmitter.h>
#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <Security/Security.h>
#import <CommonCrypto/CommonDigest.h>
#import <sys/sysctl.h>
#import <dlfcn.h>
#import <mach-o/dyld.h>

@interface RNSecurityModule : NSObject <RCTBridgeModule>
@property (nonatomic, strong) NSMutableDictionary *certificatePins;
@property (nonatomic, strong) NSURLSession *pinnedSession;
@end

@implementation RNSecurityModule

RCT_EXPORT_MODULE();

- (instancetype)init {
    self = [super init];
    if (self) {
        _certificatePins = [NSMutableDictionary dictionary];
    }
    return self;
}

#pragma mark - Jailbreak Detection

RCT_EXPORT_METHOD(checkJailbreak:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    BOOL isJailbroken = NO;
    
    // Method 1: Check for jailbreak files
    NSArray *jailbreakPaths = @[
        @"/Applications/Cydia.app",
        @"/Applications/FakeCarrier.app",
        @"/Applications/Icy.app",
        @"/Applications/IntelliScreen.app",
        @"/Applications/SBSettings.app",
        @"/Applications/WinterBoard.app",
        @"/Applications/blackra1n.app",
        @"/Library/MobileSubstrate/MobileSubstrate.dylib",
        @"/Library/MobileSubstrate/DynamicLibraries/LiveClock.plist",
        @"/Library/MobileSubstrate/DynamicLibraries/Veency.plist",
        @"/Library/Frameworks/CydiaSubstrate.framework",
        @"/System/Library/LaunchDaemons/com.ikey.bbot.plist",
        @"/System/Library/LaunchDaemons/com.saurik.Cydia.Startup.plist",
        @"/bin/bash",
        @"/bin/sh",
        @"/usr/sbin/sshd",
        @"/usr/bin/ssh",
        @"/usr/libexec/ssh-keysign",
        @"/usr/libexec/sftp-server",
        @"/etc/ssh/sshd_config",
        @"/etc/apt",
        @"/private/var/lib/apt/",
        @"/private/var/lib/cydia",
        @"/private/var/mobile/Library/SBSettings/Themes",
        @"/private/var/stash",
        @"/private/var/tmp/cydia.log",
        @"/var/cache/apt",
        @"/var/lib/apt",
        @"/var/lib/cydia"
    ];
    
    for (NSString *path in jailbreakPaths) {
        if ([[NSFileManager defaultManager] fileExistsAtPath:path]) {
            isJailbroken = YES;
            break;
        }
    }
    
    // Method 2: Check if we can write outside sandbox
    if (!isJailbroken) {
        NSString *testPath = [NSString stringWithFormat:@"/private/test_%d.txt", arc4random()];
        NSString *testString = @"jailbreak_test";
        NSError *error;
        
        [testString writeToFile:testPath atomically:YES encoding:NSUTF8StringEncoding error:&error];
        if (!error) {
            [[NSFileManager defaultManager] removeItemAtPath:testPath error:nil];
            isJailbroken = YES;
        }
    }
    
    // Method 3: Check for suspicious URL schemes
    if (!isJailbroken) {
        NSArray *suspiciousSchemes = @[@"cydia://", @"sileo://", @"zbra://", @"installer://", @"filza://"];
        for (NSString *scheme in suspiciousSchemes) {
            if ([[UIApplication sharedApplication] canOpenURL:[NSURL URLWithString:scheme]]) {
                isJailbroken = YES;
                break;
            }
        }
    }
    
    // Method 4: Check for symbolic links
    if (!isJailbroken) {
        struct stat sym;
        if (lstat("/Applications", &sym) == 0 && (sym.st_mode & S_IFLNK) == S_IFLNK) {
            isJailbroken = YES;
        }
    }
    
    // Method 5: Check loaded dynamic libraries
    if (!isJailbroken) {
        NSArray *suspiciousLibraries = @[
            @"SubstrateLoader.dylib",
            @"MobileSubstrate.dylib",
            @"TweakInject.dylib",
            @"CydiaSubstrate.dylib",
            @"cynject",
            @"libcycript",
            @"frida",
            @"fridagadget"
        ];
        
        for (int i = 0; i < _dyld_image_count(); i++) {
            const char *imageName = _dyld_get_image_name(i);
            NSString *imageNameStr = [NSString stringWithUTF8String:imageName];
            
            for (NSString *library in suspiciousLibraries) {
                if ([imageNameStr containsString:library]) {
                    isJailbroken = YES;
                    break;
                }
            }
            if (isJailbroken) break;
        }
    }
    
    // Method 6: Fork detection
    if (!isJailbroken) {
        pid_t pid = fork();
        if (pid >= 0) {
            // Fork succeeded (shouldn't happen on non-jailbroken device)
            if (pid == 0) {
                exit(0);
            }
            isJailbroken = YES;
        }
    }
    
    resolve(@(isJailbroken));
}

RCT_EXPORT_METHOD(canOpenURL:(NSString *)urlString
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    NSURL *url = [NSURL URLWithString:urlString];
    BOOL canOpen = [[UIApplication sharedApplication] canOpenURL:url];
    resolve(@(canOpen));
}

RCT_EXPORT_METHOD(isDebuggerAttached:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    #ifdef DEBUG
        resolve(@YES);
    #else
        // Check using sysctl
        int mib[4];
        struct kinfo_proc info;
        size_t size = sizeof(info);
        
        info.kp_proc.p_flag = 0;
        
        mib[0] = CTL_KERN;
        mib[1] = KERN_PROC;
        mib[2] = KERN_PROC_PID;
        mib[3] = getpid();
        
        sysctl(mib, 4, &info, &size, NULL, 0);
        
        BOOL isDebugged = (info.kp_proc.p_flag & P_TRACED) != 0;
        
        // Additional check for ptrace
        typedef int (*ptrace_ptr_t)(int _request, pid_t _pid, caddr_t _addr, int _data);
        void *handle = dlopen(NULL, RTLD_GLOBAL | RTLD_NOW);
        ptrace_ptr_t ptrace_ptr = dlsym(handle, "ptrace");
        
        if (ptrace_ptr) {
            ptrace_ptr(31, 0, 0, 0); // PT_DENY_ATTACH
        }
        
        resolve(@(isDebugged));
    #endif
}

#pragma mark - Certificate Pinning

RCT_EXPORT_METHOD(configureCertificatePinning:(NSArray *)pinConfiguration
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    @try {
        [self.certificatePins removeAllObjects];
        
        for (NSDictionary *config in pinConfiguration) {
            NSString *host = config[@"host"];
            NSArray *pins = config[@"pins"];
            NSArray *backupPins = config[@"backupPins"];
            BOOL includeSubdomains = [config[@"includeSubdomains"] boolValue];
            
            NSMutableArray *allPins = [NSMutableArray array];
            [allPins addObjectsFromArray:pins];
            if (backupPins) {
                [allPins addObjectsFromArray:backupPins];
            }
            
            self.certificatePins[host] = @{
                @"pins": allPins,
                @"includeSubdomains": @(includeSubdomains)
            };
        }
        
        // Configure URLSession with pinning
        NSURLSessionConfiguration *config = [NSURLSessionConfiguration defaultSessionConfiguration];
        self.pinnedSession = [NSURLSession sessionWithConfiguration:config
                                                           delegate:self
                                                      delegateQueue:nil];
        
        resolve(@YES);
    } @catch (NSException *exception) {
        reject(@"CONFIG_ERROR", @"Failed to configure certificate pinning", nil);
    }
}

RCT_EXPORT_METHOD(getCertificateChain:(NSString *)hostname
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    // This would need to make a test connection to get the certificate chain
    // For now, returning empty array
    resolve(@[]);
}

#pragma mark - Security Hardening

RCT_EXPORT_METHOD(enableAntiDebugging:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    #ifndef DEBUG
        // Prevent debugging with ptrace
        typedef int (*ptrace_ptr_t)(int _request, pid_t _pid, caddr_t _addr, int _data);
        void *handle = dlopen(NULL, RTLD_GLOBAL | RTLD_NOW);
        ptrace_ptr_t ptrace_ptr = dlsym(handle, "ptrace");
        
        if (ptrace_ptr) {
            ptrace_ptr(31, 0, 0, 0); // PT_DENY_ATTACH
        }
        
        // Additional anti-debugging techniques
        dispatch_source_t timer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0));
        dispatch_source_set_timer(timer, DISPATCH_TIME_NOW, 1 * NSEC_PER_SEC, 0);
        dispatch_source_set_event_handler(timer, ^{
            // Check for debugger periodically
            int mib[4];
            struct kinfo_proc info;
            size_t size = sizeof(info);
            
            info.kp_proc.p_flag = 0;
            
            mib[0] = CTL_KERN;
            mib[1] = KERN_PROC;
            mib[2] = KERN_PROC_PID;
            mib[3] = getpid();
            
            sysctl(mib, 4, &info, &size, NULL, 0);
            
            if ((info.kp_proc.p_flag & P_TRACED) != 0) {
                // Debugger detected, exit
                exit(0);
            }
        });
        dispatch_resume(timer);
    #endif
    
    resolve(@YES);
}

RCT_EXPORT_METHOD(enableBackgroundBlur:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    dispatch_async(dispatch_get_main_queue(), ^{
        // Add observer for app backgrounding
        [[NSNotificationCenter defaultCenter] addObserverForName:UIApplicationWillResignActiveNotification
                                                          object:nil
                                                           queue:[NSOperationQueue mainQueue]
                                                      usingBlock:^(NSNotification *note) {
            // Add blur view to prevent screenshot of sensitive data
            UIWindow *window = [UIApplication sharedApplication].keyWindow;
            UIVisualEffectView *blurView = [[UIVisualEffectView alloc] initWithEffect:[UIBlurEffect effectWithStyle:UIBlurEffectStyleRegular]];
            blurView.frame = window.bounds;
            blurView.tag = 99999;
            [window addSubview:blurView];
        }];
        
        [[NSNotificationCenter defaultCenter] addObserverForName:UIApplicationDidBecomeActiveNotification
                                                          object:nil
                                                           queue:[NSOperationQueue mainQueue]
                                                      usingBlock:^(NSNotification *note) {
            // Remove blur view
            UIWindow *window = [UIApplication sharedApplication].keyWindow;
            [[window viewWithTag:99999] removeFromSuperview];
        }];
        
        resolve(@YES);
    });
}

#pragma mark - Network Security

RCT_EXPORT_METHOD(checkVPN:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    BOOL isVPNActive = NO;
    
    // Check for VPN interfaces
    CFDictionaryRef cfDict = CFNetworkCopySystemProxySettings();
    NSDictionary *dict = (__bridge NSDictionary *)cfDict;
    
    if (dict[@"__SCOPED__"] != nil) {
        for (NSString *key in dict[@"__SCOPED__"]) {
            if ([key containsString:@"tap"] || [key containsString:@"tun"] || [key containsString:@"ppp"] || [key containsString:@"ipsec"]) {
                isVPNActive = YES;
                break;
            }
        }
    }
    
    if (cfDict) {
        CFRelease(cfDict);
    }
    
    resolve(@(isVPNActive));
}

RCT_EXPORT_METHOD(checkProxy:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    BOOL isProxyActive = NO;
    
    CFDictionaryRef cfDict = CFNetworkCopySystemProxySettings();
    NSDictionary *dict = (__bridge NSDictionary *)cfDict;
    
    if ([dict[@"HTTPSEnable"] intValue] == 1 || [dict[@"HTTPEnable"] intValue] == 1) {
        isProxyActive = YES;
    }
    
    if (cfDict) {
        CFRelease(cfDict);
    }
    
    resolve(@(isProxyActive));
}

#pragma mark - Code Integrity

RCT_EXPORT_METHOD(verifyCodeIntegrity:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject) {
    // Check code signature
    SecCodeRef code = NULL;
    OSStatus status = SecCodeCopySelf(kSecCSDefaultFlags, &code);
    
    if (status == errSecSuccess) {
        SecRequirementRef requirement = NULL;
        status = SecRequirementCreateWithString(CFSTR("anchor apple generic"), kSecCSDefaultFlags, &requirement);
        
        if (status == errSecSuccess) {
            status = SecCodeCheckValidity(code, kSecCSDefaultFlags, requirement);
            CFRelease(requirement);
        }
        
        CFRelease(code);
    }
    
    resolve(@(status == errSecSuccess));
}

#pragma mark - URLSession Delegate for Certificate Pinning

- (void)URLSession:(NSURLSession *)session
              task:(NSURLSessionTask *)task
didReceiveChallenge:(NSURLAuthenticationChallenge *)challenge
 completionHandler:(void (^)(NSURLSessionAuthChallengeDisposition disposition, NSURLCredential *credential))completionHandler {
    
    if ([challenge.protectionSpace.authenticationMethod isEqualToString:NSURLAuthenticationMethodServerTrust]) {
        NSString *host = challenge.protectionSpace.host;
        NSDictionary *pinConfig = [self findPinConfigForHost:host];
        
        if (pinConfig) {
            SecTrustRef serverTrust = challenge.protectionSpace.serverTrust;
            NSArray *pins = pinConfig[@"pins"];
            
            // Evaluate server trust
            SecTrustResultType result;
            OSStatus status = SecTrustEvaluate(serverTrust, &result);
            
            if (status == errSecSuccess && (result == kSecTrustResultUnspecified || result == kSecTrustResultProceed)) {
                // Get certificate chain
                NSMutableArray *certificateChainPins = [NSMutableArray array];
                CFIndex certificateCount = SecTrustGetCertificateCount(serverTrust);
                
                for (CFIndex i = 0; i < certificateCount; i++) {
                    SecCertificateRef certificate = SecTrustGetCertificateAtIndex(serverTrust, i);
                    NSString *pin = [self pinForCertificate:certificate];
                    if (pin) {
                        [certificateChainPins addObject:pin];
                    }
                }
                
                // Check if any pin matches
                BOOL pinMatched = NO;
                for (NSString *pin in pins) {
                    if ([certificateChainPins containsObject:pin]) {
                        pinMatched = YES;
                        break;
                    }
                }
                
                if (pinMatched) {
                    NSURLCredential *credential = [NSURLCredential credentialForTrust:serverTrust];
                    completionHandler(NSURLSessionAuthChallengeUseCredential, credential);
                    return;
                }
            }
        }
    }
    
    // Default handling
    completionHandler(NSURLSessionAuthChallengePerformDefaultHandling, nil);
}

- (NSDictionary *)findPinConfigForHost:(NSString *)host {
    // Direct match
    if (self.certificatePins[host]) {
        return self.certificatePins[host];
    }
    
    // Check wildcard and subdomain matches
    for (NSString *configHost in self.certificatePins) {
        NSDictionary *config = self.certificatePins[configHost];
        BOOL includeSubdomains = [config[@"includeSubdomains"] boolValue];
        
        if (includeSubdomains) {
            if ([configHost hasPrefix:@"*."]) {
                NSString *baseDomain = [configHost substringFromIndex:2];
                if ([host hasSuffix:baseDomain]) {
                    return config;
                }
            } else if ([host hasSuffix:[@"." stringByAppendingString:configHost]]) {
                return config;
            }
        }
    }
    
    return nil;
}

- (NSString *)pinForCertificate:(SecCertificateRef)certificate {
    NSData *certificateData = (__bridge_transfer NSData *)SecCertificateCopyData(certificate);
    NSData *publicKeyData = [self publicKeyDataForCertificate:certificate];
    
    if (!publicKeyData) {
        return nil;
    }
    
    // Calculate SHA256 of public key
    unsigned char sha256Buffer[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(publicKeyData.bytes, (CC_LONG)publicKeyData.length, sha256Buffer);
    NSData *sha256Data = [NSData dataWithBytes:sha256Buffer length:CC_SHA256_DIGEST_LENGTH];
    
    // Convert to base64
    return [sha256Data base64EncodedStringWithOptions:0];
}

- (NSData *)publicKeyDataForCertificate:(SecCertificateRef)certificate {
    SecKeyRef publicKey = NULL;
    SecTrustRef trust = NULL;
    SecTrustResultType result;
    
    SecPolicyRef policy = SecPolicyCreateBasicX509();
    OSStatus status = SecTrustCreateWithCertificates(certificate, policy, &trust);
    
    if (status == errSecSuccess) {
        status = SecTrustEvaluate(trust, &result);
        if (status == errSecSuccess) {
            publicKey = SecTrustCopyPublicKey(trust);
        }
    }
    
    if (policy) CFRelease(policy);
    if (trust) CFRelease(trust);
    
    if (!publicKey) {
        return nil;
    }
    
    NSData *publicKeyData = (__bridge_transfer NSData *)SecKeyCopyExternalRepresentation(publicKey, NULL);
    CFRelease(publicKey);
    
    return publicKeyData;
}

@end