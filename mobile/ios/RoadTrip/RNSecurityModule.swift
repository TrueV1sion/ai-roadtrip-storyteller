import Foundation
import React

@objc(RNSecurityModule)
class RNSecurityModule: NSObject {
  
  // Session configuration with certificate pinning
  private var pinnedHosts: [String: [String]] = [:]
  private var sessionDelegate: CertificatePinningDelegate?
  
  @objc
  static func requiresMainQueueSetup() -> Bool {
    return false
  }
  
  @objc
  func configureCertificatePinning(_ config: [[String: Any]], 
                                   resolver: @escaping RCTPromiseResolveBlock,
                                   rejecter: @escaping RCTPromiseRejectBlock) {
    DispatchQueue.main.async {
      // Clear existing pins
      self.pinnedHosts.removeAll()
      
      // Configure new pins
      for pinConfig in config {
        guard let host = pinConfig["host"] as? String,
              let pins = pinConfig["pins"] as? [String] else {
          continue
        }
        
        var allPins = pins
        if let backupPins = pinConfig["backupPins"] as? [String] {
          allPins.append(contentsOf: backupPins)
        }
        
        self.pinnedHosts[host] = allPins
      }
      
      // Create session delegate
      self.sessionDelegate = CertificatePinningDelegate(pinnedHosts: self.pinnedHosts)
      
      // Configure URLSession
      self.configureURLSession()
      
      resolver(true)
    }
  }
  
  @objc
  func getCertificateChain(_ hostname: String,
                           resolver: @escaping RCTPromiseResolveBlock,
                           rejecter: @escaping RCTPromiseRejectBlock) {
    // Create a test connection to get the certificate chain
    guard let url = URL(string: "https://\(hostname)") else {
      rejecter("INVALID_URL", "Invalid hostname", nil)
      return
    }
    
    let session = URLSession(configuration: .ephemeral, 
                            delegate: CertificateChainDelegate(resolver: resolver, rejecter: rejecter),
                            delegateQueue: nil)
    
    let task = session.dataTask(with: url) { _, _, _ in
      // We don't care about the response, just the certificate chain
    }
    
    task.resume()
  }
  
  private func configureURLSession() {
    // Configure the default URLSession to use our certificate pinning delegate
    URLSession.shared.configuration.urlCache = nil
    URLSession.shared.configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
  }
  
  // Certificate Pinning Delegate
  class CertificatePinningDelegate: NSObject, URLSessionDelegate {
    private let pinnedHosts: [String: [String]]
    
    init(pinnedHosts: [String: [String]]) {
      self.pinnedHosts = pinnedHosts
      super.init()
    }
    
    func urlSession(_ session: URLSession, 
                    didReceive challenge: URLAuthenticationChallenge, 
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
      
      guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
            let serverTrust = challenge.protectionSpace.serverTrust else {
        completionHandler(.performDefaultHandling, nil)
        return
      }
      
      let host = challenge.protectionSpace.host
      
      // Check if we have pins for this host
      guard let pins = pinnedHosts[host] ?? findPinsForHost(host) else {
        // No pins configured for this host
        completionHandler(.performDefaultHandling, nil)
        return
      }
      
      // Validate certificate chain
      if validateCertificateChain(serverTrust: serverTrust, pins: pins) {
        let credential = URLCredential(trust: serverTrust)
        completionHandler(.useCredential, credential)
      } else {
        completionHandler(.cancelAuthenticationChallenge, nil)
      }
    }
    
    private func findPinsForHost(_ host: String) -> [String]? {
      // Check for wildcard matches
      for (pinnedHost, pins) in pinnedHosts {
        if pinnedHost.hasPrefix("*.") {
          let baseDomain = String(pinnedHost.dropFirst(2))
          if host.hasSuffix(baseDomain) {
            return pins
          }
        }
      }
      return nil
    }
    
    private func validateCertificateChain(serverTrust: SecTrust, pins: [String]) -> Bool {
      // Get certificate chain
      let certificateCount = SecTrustGetCertificateCount(serverTrust)
      
      for i in 0..<certificateCount {
        guard let certificate = SecTrustGetCertificateAtIndex(serverTrust, i) else {
          continue
        }
        
        // Get public key
        guard let publicKey = SecCertificateCopyPublicKey(certificate) else {
          continue
        }
        
        // Get public key data
        guard let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, nil) as Data? else {
          continue
        }
        
        // Calculate SHA256 hash
        let hash = publicKeyData.sha256()
        let base64Hash = hash.base64EncodedString()
        
        // Check if this pin matches any of our pins
        if pins.contains(base64Hash) {
          return true
        }
      }
      
      return false
    }
  }
  
  // Certificate Chain Delegate
  class CertificateChainDelegate: NSObject, URLSessionDelegate {
    private let resolver: RCTPromiseResolveBlock
    private let rejecter: RCTPromiseRejectBlock
    
    init(resolver: @escaping RCTPromiseResolveBlock, rejecter: @escaping RCTPromiseRejectBlock) {
      self.resolver = resolver
      self.rejecter = rejecter
      super.init()
    }
    
    func urlSession(_ session: URLSession, 
                    didReceive challenge: URLAuthenticationChallenge, 
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
      
      guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
            let serverTrust = challenge.protectionSpace.serverTrust else {
        completionHandler(.performDefaultHandling, nil)
        return
      }
      
      // Extract certificate chain
      var certificateChain: [String] = []
      let certificateCount = SecTrustGetCertificateCount(serverTrust)
      
      for i in 0..<certificateCount {
        guard let certificate = SecTrustGetCertificateAtIndex(serverTrust, i),
              let publicKey = SecCertificateCopyPublicKey(certificate),
              let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, nil) as Data? else {
          continue
        }
        
        let hash = publicKeyData.sha256()
        let base64Hash = hash.base64EncodedString()
        certificateChain.append(base64Hash)
      }
      
      // Resolve with certificate chain
      resolver(certificateChain)
      
      // Cancel the request
      completionHandler(.cancelAuthenticationChallenge, nil)
    }
  }
}

// SHA256 extension for Data
extension Data {
  func sha256() -> Data {
    var hash = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
    self.withUnsafeBytes {
      _ = CC_SHA256($0.baseAddress, CC_LONG(self.count), &hash)
    }
    return Data(hash)
  }
}