/**
 * Android Security Module Implementation
 * Certificate pinning and root detection for Android
 */

package com.roadtrip.security;

import android.app.Activity;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import android.os.Debug;
import android.provider.Settings;
import android.view.WindowManager;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.ReadableArray;
import com.facebook.react.bridge.ReadableMap;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.module.annotations.ReactModule;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.security.MessageDigest;
import java.security.cert.Certificate;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLPeerUnverifiedException;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

import okhttp3.CertificatePinner;
import okhttp3.OkHttpClient;

@ReactModule(name = RNSecurityModule.NAME)
public class RNSecurityModule extends ReactContextBaseJavaModule {
    public static final String NAME = "RNSecurityModule";
    
    private final ReactApplicationContext reactContext;
    private Map<String, CertificatePinConfig> certificatePins = new HashMap<>();
    private OkHttpClient pinnedHttpClient;
    
    // Root detection paths
    private static final String[] ROOT_PATHS = {
        "/system/app/Superuser.apk",
        "/system/app/SuperSU.apk",
        "/sbin/su",
        "/system/bin/su",
        "/system/xbin/su",
        "/data/local/xbin/su",
        "/data/local/bin/su",
        "/system/sd/xbin/su",
        "/system/bin/failsafe/su",
        "/data/local/su",
        "/su/bin/su",
        "/system/bin/.ext/.su",
        "/system/usr/we-need-root/su-backup",
        "/system/xbin/mu",
        "/system/bin/magisk",
        "/data/adb/magisk",
        "/sbin/.magisk",
        "/data/adb/ksu",
        "/data/adb/ksud",
        "/system/xbin/busybox",
        "/system/bin/busybox",
        "/data/local/bin/busybox"
    };
    
    // Root packages
    private static final String[] ROOT_PACKAGES = {
        "com.koushikdutta.superuser",
        "com.koushikdutta.rommanager",
        "com.noshufou.android.su",
        "com.noshufou.android.su.elite",
        "eu.chainfire.supersu",
        "com.thirdparty.superuser",
        "com.yellowes.su",
        "com.topjohnwu.magisk",
        "com.kingroot.kinguser",
        "com.kingo.root",
        "com.smedialink.oneclean",
        "com.zhiqupk.root.global",
        "com.alephzain.framaroot",
        "com.devadvance.rootcloak",
        "com.devadvance.rootcloakplus",
        "com.zachspong.temprootremovejb",
        "com.amphoras.hidemyroot",
        "com.formyhm.hiderootPremium",
        "com.formyhm.hideroot",
        "com.chelpus.lackypatch",
        "com.dimonvideo.luckypatcher",
        "com.android.vending.billing.InAppBillingService.COIN",
        "com.android.vending.billing.InAppBillingService.LUCK"
    };
    
    // Dangerous properties
    private static final Map<String, String> DANGEROUS_PROPS = new HashMap<>();
    static {
        DANGEROUS_PROPS.put("ro.debuggable", "1");
        DANGEROUS_PROPS.put("ro.secure", "0");
        DANGEROUS_PROPS.put("service.adb.root", "1");
        DANGEROUS_PROPS.put("ro.build.selinux", "0");
    }
    
    public RNSecurityModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
    }
    
    @Override
    public String getName() {
        return NAME;
    }
    
    // Root Detection Methods
    
    @ReactMethod
    public void checkPackages(String packageName, Promise promise) {
        try {
            PackageManager pm = reactContext.getPackageManager();
            pm.getPackageInfo(packageName, 0);
            promise.resolve(true);
        } catch (PackageManager.NameNotFoundException e) {
            promise.resolve(false);
        }
    }
    
    @ReactMethod
    public void checkSuAccess(Promise promise) {
        try {
            // Method 1: Try to execute su
            Runtime runtime = Runtime.getRuntime();
            Process process = runtime.exec(new String[]{"which", "su"});
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line = reader.readLine();
            reader.close();
            process.destroy();
            
            if (line != null && line.length() > 0) {
                promise.resolve(true);
                return;
            }
            
            // Method 2: Try to execute su directly
            try {
                process = runtime.exec("su");
                process.destroy();
                promise.resolve(true);
                return;
            } catch (Exception e) {
                // Expected on non-rooted devices
            }
            
            promise.resolve(false);
        } catch (Exception e) {
            promise.resolve(false);
        }
    }
    
    @ReactMethod
    public void getBuildProperty(String property, Promise promise) {
        try {
            String value = getSystemProperty(property);
            promise.resolve(value);
        } catch (Exception e) {
            promise.resolve(null);
        }
    }
    
    @ReactMethod
    public void getSELinuxStatus(Promise promise) {
        try {
            // Method 1: Check via system property
            String selinux = getSystemProperty("ro.build.selinux");
            if ("1".equals(selinux)) {
                // Check enforcing status
                Process process = Runtime.getRuntime().exec("getenforce");
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String line = reader.readLine();
                reader.close();
                process.destroy();
                promise.resolve(line);
                return;
            }
            
            // Method 2: Check /sys/fs/selinux/enforce
            File selinuxEnforce = new File("/sys/fs/selinux/enforce");
            if (selinuxEnforce.exists()) {
                FileInputStream fis = new FileInputStream(selinuxEnforce);
                int enforcing = fis.read();
                fis.close();
                promise.resolve(enforcing == '1' ? "Enforcing" : "Permissive");
                return;
            }
            
            promise.resolve("Disabled");
        } catch (Exception e) {
            promise.resolve("Unknown");
        }
    }
    
    @ReactMethod
    public void isDebuggerConnected(Promise promise) {
        boolean debugged = Debug.isDebuggerConnected();
        
        // Additional check for wait for debugger
        if (!debugged) {
            debugged = Debug.waitingForDebugger();
        }
        
        // Check if app is debuggable
        if (!debugged) {
            try {
                ApplicationInfo appInfo = reactContext.getApplicationInfo();
                debugged = (appInfo.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
            } catch (Exception e) {
                // Ignore
            }
        }
        
        promise.resolve(debugged);
    }
    
    // Certificate Pinning Methods
    
    @ReactMethod
    public void configureCertificatePinning(ReadableArray pinConfiguration, Promise promise) {
        try {
            certificatePins.clear();
            CertificatePinner.Builder pinnerBuilder = new CertificatePinner.Builder();
            
            for (int i = 0; i < pinConfiguration.size(); i++) {
                ReadableMap config = pinConfiguration.getMap(i);
                String domain = config.getString("domain");
                boolean includeSubdomains = config.getBoolean("includeSubdomains");
                ReadableMap pinSet = config.getMap("pinSet");
                ReadableArray pins = pinSet.getArray("pins");
                
                // Add pins to OkHttp pinner
                for (int j = 0; j < pins.size(); j++) {
                    ReadableMap pin = pins.getMap(j);
                    String digest = pin.getString("digest");
                    String value = pin.getString("value");
                    
                    if ("SHA-256".equals(digest)) {
                        String pinPattern = includeSubdomains ? "**." + domain : domain;
                        pinnerBuilder.add(pinPattern, "sha256/" + value);
                    }
                }
                
                // Store configuration
                CertificatePinConfig pinConfig = new CertificatePinConfig();
                pinConfig.domain = domain;
                pinConfig.includeSubdomains = includeSubdomains;
                pinConfig.pins = new ArrayList<>();
                
                for (int j = 0; j < pins.size(); j++) {
                    ReadableMap pin = pins.getMap(j);
                    pinConfig.pins.add(pin.getString("value"));
                }
                
                certificatePins.put(domain, pinConfig);
            }
            
            // Build OkHttp client with certificate pinning
            pinnedHttpClient = new OkHttpClient.Builder()
                .certificatePinner(pinnerBuilder.build())
                .build();
            
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("CONFIG_ERROR", "Failed to configure certificate pinning", e);
        }
    }
    
    @ReactMethod
    public void getCertificateChain(String hostname, Promise promise) {
        try {
            WritableArray chain = Arguments.createArray();
            
            // Create a trust manager to capture certificates
            TrustManager[] trustManagers = new TrustManager[] {
                new X509TrustManager() {
                    @Override
                    public void checkClientTrusted(X509Certificate[] chain, String authType) {}
                    
                    @Override
                    public void checkServerTrusted(X509Certificate[] chain, String authType) throws CertificateException {
                        // Capture the certificate chain
                        for (X509Certificate cert : chain) {
                            try {
                                // Get public key and calculate SHA256
                                byte[] publicKey = cert.getPublicKey().getEncoded();
                                MessageDigest md = MessageDigest.getInstance("SHA-256");
                                byte[] digest = md.digest(publicKey);
                                String pin = android.util.Base64.encodeToString(digest, android.util.Base64.NO_WRAP);
                                WritableArray chainArray = Arguments.createArray();
                                chainArray.pushString(pin);
                            } catch (Exception e) {
                                // Ignore
                            }
                        }
                    }
                    
                    @Override
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[0];
                    }
                }
            };
            
            // Make a test connection to get certificates
            SSLContext sslContext = SSLContext.getInstance("TLS");
            sslContext.init(null, trustManagers, null);
            
            HttpsURLConnection connection = (HttpsURLConnection) new java.net.URL("https://" + hostname).openConnection();
            connection.setSSLSocketFactory(sslContext.getSocketFactory());
            connection.setHostnameVerifier(new HostnameVerifier() {
                @Override
                public boolean verify(String hostname, SSLSession session) {
                    return true;
                }
            });
            
            connection.connect();
            
            Certificate[] serverCerts = connection.getServerCertificates();
            for (Certificate cert : serverCerts) {
                if (cert instanceof X509Certificate) {
                    X509Certificate x509Cert = (X509Certificate) cert;
                    byte[] publicKey = x509Cert.getPublicKey().getEncoded();
                    MessageDigest md = MessageDigest.getInstance("SHA-256");
                    byte[] digest = md.digest(publicKey);
                    String pin = android.util.Base64.encodeToString(digest, android.util.Base64.NO_WRAP);
                    chain.pushString(pin);
                }
            }
            
            connection.disconnect();
            promise.resolve(chain);
        } catch (Exception e) {
            promise.resolve(Arguments.createArray());
        }
    }
    
    // Security Hardening Methods
    
    @ReactMethod
    public void setScreenshotBlocking(boolean enabled, Promise promise) {
        Activity activity = getCurrentActivity();
        if (activity != null) {
            activity.runOnUiThread(() -> {
                try {
                    if (enabled) {
                        activity.getWindow().setFlags(
                            WindowManager.LayoutParams.FLAG_SECURE,
                            WindowManager.LayoutParams.FLAG_SECURE
                        );
                    } else {
                        activity.getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
                    }
                    promise.resolve(true);
                } catch (Exception e) {
                    promise.reject("WINDOW_ERROR", "Failed to set screenshot blocking", e);
                }
            });
        } else {
            promise.reject("NO_ACTIVITY", "No activity available");
        }
    }
    
    @ReactMethod
    public void enableAntiDebugging(Promise promise) {
        // Set up anti-debugging thread
        new Thread(() -> {
            while (true) {
                if (Debug.isDebuggerConnected() || Debug.waitingForDebugger()) {
                    // Debugger detected, exit
                    android.os.Process.killProcess(android.os.Process.myPid());
                    System.exit(0);
                }
                
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }).start();
        
        promise.resolve(true);
    }
    
    @ReactMethod
    public void verifyCodeIntegrity(Promise promise) {
        try {
            Context context = reactContext.getApplicationContext();
            PackageInfo packageInfo = context.getPackageManager().getPackageInfo(
                context.getPackageName(),
                PackageManager.GET_SIGNATURES
            );
            
            // Get current signatures
            Signature[] signatures = packageInfo.signatures;
            
            // TODO: Compare with known good signatures
            // For now, just check if signatures exist
            boolean hasSignatures = signatures != null && signatures.length > 0;
            
            promise.resolve(hasSignatures);
        } catch (Exception e) {
            promise.resolve(false);
        }
    }
    
    // Network Security Methods
    
    @ReactMethod
    public void checkVPN(Promise promise) {
        try {
            boolean vpnActive = false;
            
            // Method 1: Check network interfaces
            Enumeration<NetworkInterface> networkInterfaces = NetworkInterface.getNetworkInterfaces();
            while (networkInterfaces.hasMoreElements()) {
                NetworkInterface ni = networkInterfaces.nextElement();
                String name = ni.getName();
                if (name.contains("tun") || name.contains("tap") || name.contains("ppp") || name.contains("ipsec")) {
                    vpnActive = true;
                    break;
                }
            }
            
            // Method 2: Check VPN service (requires API 21+)
            if (!vpnActive && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                try {
                    android.net.ConnectivityManager cm = (android.net.ConnectivityManager) 
                        reactContext.getSystemService(Context.CONNECTIVITY_SERVICE);
                    android.net.Network[] networks = cm.getAllNetworks();
                    
                    for (android.net.Network network : networks) {
                        android.net.NetworkCapabilities caps = cm.getNetworkCapabilities(network);
                        if (caps != null && caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_VPN)) {
                            vpnActive = true;
                            break;
                        }
                    }
                } catch (Exception e) {
                    // Ignore
                }
            }
            
            promise.resolve(vpnActive);
        } catch (Exception e) {
            promise.resolve(false);
        }
    }
    
    @ReactMethod
    public void checkProxy(Promise promise) {
        try {
            boolean proxyActive = false;
            
            // Check system proxy settings
            String proxyHost = System.getProperty("http.proxyHost");
            String proxyPort = System.getProperty("http.proxyPort");
            
            if (proxyHost != null && proxyHost.length() > 0 && proxyPort != null && proxyPort.length() > 0) {
                proxyActive = true;
            }
            
            // Check HTTPS proxy
            if (!proxyActive) {
                proxyHost = System.getProperty("https.proxyHost");
                proxyPort = System.getProperty("https.proxyPort");
                
                if (proxyHost != null && proxyHost.length() > 0 && proxyPort != null && proxyPort.length() > 0) {
                    proxyActive = true;
                }
            }
            
            // Check Android proxy settings
            if (!proxyActive && Build.VERSION.SDK_INT >= Build.VERSION_CODES.ICE_CREAM_SANDWICH) {
                String host = System.getProperty("http.proxyHost");
                String port = System.getProperty("http.proxyPort");
                
                if (host == null) {
                    host = android.net.Proxy.getDefaultHost();
                }
                
                if (port == null) {
                    int portNum = android.net.Proxy.getDefaultPort();
                    if (portNum > 0) {
                        port = String.valueOf(portNum);
                    }
                }
                
                proxyActive = host != null && port != null;
            }
            
            promise.resolve(proxyActive);
        } catch (Exception e) {
            promise.resolve(false);
        }
    }
    
    // Utility Methods
    
    private String getSystemProperty(String key) {
        try {
            Class<?> systemProperties = Class.forName("android.os.SystemProperties");
            Method get = systemProperties.getMethod("get", String.class);
            return (String) get.invoke(null, key);
        } catch (Exception e) {
            return null;
        }
    }
    
    // Certificate Pin Configuration
    private static class CertificatePinConfig {
        String domain;
        boolean includeSubdomains;
        List<String> pins;
    }
}