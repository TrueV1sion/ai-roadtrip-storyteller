#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(RNSecurityModule, NSObject)

RCT_EXTERN_METHOD(configureCertificatePinning:(NSArray *)config
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getCertificateChain:(NSString *)hostname
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end