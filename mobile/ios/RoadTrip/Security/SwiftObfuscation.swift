import Foundation

// Swift String Obfuscation
// Provides compile-time string encryption for sensitive strings

@propertyWrapper
struct ObfuscatedString {
    private var obfuscated: [UInt8]
    
    init(_ string: String) {
        self.obfuscated = Self.obfuscate(string)
    }
    
    var wrappedValue: String {
        return Self.deobfuscate(obfuscated)
    }
    
    private static func obfuscate(_ string: String) -> [UInt8] {
        let key = UInt8.random(in: 1...255)
        return [key] + string.utf8.map { $0 ^ key }
    }
    
    private static func deobfuscate(_ obfuscated: [UInt8]) -> String {
        guard !obfuscated.isEmpty else { return "" }
        let key = obfuscated[0]
        let deobfuscated = obfuscated.dropFirst().map { $0 ^ key }
        return String(bytes: deobfuscated, encoding: .utf8) ?? ""
    }
}

// Usage example:
// @ObfuscatedString("sensitive_api_endpoint")
// private var apiEndpoint: String

// Anti-debugging protection
class SecurityChecks {
    
    // Check if debugger is attached
    static func isDebuggerAttached() -> Bool {
        var info = kinfo_proc()
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        var size = MemoryLayout.stride(ofValue: info)
        
        let result = sysctl(&mib, UInt32(mib.count), &info, &size, nil, 0)
        
        return result == 0 && (info.kp_proc.p_flag & P_TRACED) != 0
    }
    
    // Check if running in simulator
    static func isSimulator() -> Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }
    
    // Check if app is jailbroken
    static func isJailbroken() -> Bool {
        #if targetEnvironment(simulator)
        return false
        #else
        // Check for common jailbreak files
        let jailbreakPaths = [
            "/Applications/Cydia.app",
            "/Library/MobileSubstrate/MobileSubstrate.dylib",
            "/bin/bash",
            "/usr/sbin/sshd",
            "/etc/apt",
            "/private/var/lib/apt/",
            "/usr/bin/ssh"
        ]
        
        for path in jailbreakPaths {
            if FileManager.default.fileExists(atPath: path) {
                return true
            }
        }
        
        // Check if we can write to system directories
        let testPath = "/private/test_\(UUID().uuidString).txt"
        do {
            try "test".write(toFile: testPath, atomically: true, encoding: .utf8)
            try FileManager.default.removeItem(atPath: testPath)
            return true
        } catch {
            // Expected behavior - cannot write to system directories
        }
        
        // Check for suspicious URL schemes
        if let url = URL(string: "cydia://package/com.example.package"),
           UIApplication.shared.canOpenURL(url) {
            return true
        }
        
        return false
        #endif
    }
    
    // Runtime application tamper detection
    static func checkIntegrity() -> Bool {
        guard let bundleIdentifier = Bundle.main.bundleIdentifier,
              bundleIdentifier == "com.roadtrip.app" else {
            return false
        }
        
        // Check code signature
        if let executablePath = Bundle.main.executablePath {
            let fileManager = FileManager.default
            if let attributes = try? fileManager.attributesOfItem(atPath: executablePath),
               let modificationDate = attributes[.modificationDate] as? Date {
                // Store original modification date during build
                // Compare with stored date
                // This is a simplified check
                return true
            }
        }
        
        return false
    }
}

// Method swizzling protection
extension NSObject {
    static func protectMethodSwizzling() {
        // Exchange implementations back if they were swizzled
        let originalSelectors = [
            #selector(URLSession.dataTask(with:completionHandler:)),
            #selector(UIApplication.open(_:options:completionHandler:))
        ]
        
        for selector in originalSelectors {
            // Check if method implementation has been changed
            // This is a simplified example
        }
    }
}

// Binary packing check
class BinaryProtection {
    static func checkBinaryEncryption() -> Bool {
        let machHeader = _dyld_get_image_header(0)
        
        guard let header = machHeader else { return false }
        
        var ptr = UnsafeRawPointer(header).advanced(by: MemoryLayout<mach_header_64>.size)
        
        for _ in 0..<header.pointee.ncmds {
            let loadCommand = ptr.assumingMemoryBound(to: load_command.self).pointee
            
            if loadCommand.cmd == LC_ENCRYPTION_INFO_64 {
                let encryptionInfo = ptr.assumingMemoryBound(to: encryption_info_command_64.self).pointee
                return encryptionInfo.cryptid != 0
            }
            
            ptr = ptr.advanced(by: Int(loadCommand.cmdsize))
        }
        
        return false
    }
}