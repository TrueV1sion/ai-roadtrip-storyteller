//
//  RNCarPlay.swift
//  RoadTrip
//
//  CarPlay integration module for React Native
//

import Foundation
import CarPlay
import React

@objc(RNCarPlay)
class RNCarPlay: RCTEventEmitter, CPInterfaceControllerDelegate, CPMapTemplateDelegate, CPListTemplateDelegate {
    
    private var interfaceController: CPInterfaceController?
    private var window: CPWindow?
    private var templates: [String: CPTemplate] = [:]
    private var navigationSession: CPNavigationSession?
    private var currentManeuver: CPManeuver?
    
    // Event names
    private let EVENT_DID_CONNECT = "didConnect"
    private let EVENT_DID_DISCONNECT = "didDisconnect"
    private let EVENT_DID_SELECT_LIST_ITEM = "didSelectListItem"
    private let EVENT_DID_SELECT_MAP_BUTTON = "didSelectMapButton"
    private let EVENT_DID_UPDATE_MANEUVERS = "didUpdateManeuvers"
    private let EVENT_DID_CANCEL_NAVIGATION = "didCancelNavigation"
    private let EVENT_DID_ARRIVE = "didArrive"
    private let EVENT_DID_SELECT_VOICE_CONTROL = "didSelectVoiceControl"
    
    override init() {
        super.init()
    }
    
    override static func requiresMainQueueSetup() -> Bool {
        return true
    }
    
    override func supportedEvents() -> [String]! {
        return [
            EVENT_DID_CONNECT,
            EVENT_DID_DISCONNECT,
            EVENT_DID_SELECT_LIST_ITEM,
            EVENT_DID_SELECT_MAP_BUTTON,
            EVENT_DID_UPDATE_MANEUVERS,
            EVENT_DID_CANCEL_NAVIGATION,
            EVENT_DID_ARRIVE,
            EVENT_DID_SELECT_VOICE_CONTROL
        ]
    }
    
    // MARK: - React Native Methods
    
    @objc(setRootTemplate:resolver:rejecter:)
    func setRootTemplate(_ templateConfig: NSDictionary,
                        resolver resolve: @escaping RCTPromiseResolveBlock,
                        rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let template = self.createTemplate(from: templateConfig) else {
                reject("INVALID_TEMPLATE", "Failed to create template", nil)
                return
            }
            
            self.interfaceController?.setRootTemplate(template, animated: true, completion: { success, error in
                if success {
                    resolve(true)
                } else {
                    reject("SET_ROOT_FAILED", error?.localizedDescription ?? "Unknown error", error)
                }
            })
        }
    }
    
    @objc(pushTemplate:resolver:rejecter:)
    func pushTemplate(_ templateConfig: NSDictionary,
                     resolver resolve: @escaping RCTPromiseResolveBlock,
                     rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let template = self.createTemplate(from: templateConfig) else {
                reject("INVALID_TEMPLATE", "Failed to create template", nil)
                return
            }
            
            self.interfaceController?.pushTemplate(template, animated: true, completion: { success, error in
                if success {
                    resolve(true)
                } else {
                    reject("PUSH_FAILED", error?.localizedDescription ?? "Unknown error", error)
                }
            })
        }
    }
    
    @objc(popTemplate:rejecter:)
    func popTemplate(_ resolve: @escaping RCTPromiseResolveBlock,
                    rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            self.interfaceController?.popTemplate(animated: true, completion: { success, error in
                if success {
                    resolve(true)
                } else {
                    reject("POP_FAILED", error?.localizedDescription ?? "Unknown error", error)
                }
            })
        }
    }
    
    @objc(popToRootTemplate:rejecter:)
    func popToRootTemplate(_ resolve: @escaping RCTPromiseResolveBlock,
                          rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            self.interfaceController?.popToRootTemplate(animated: true, completion: { success, error in
                if success {
                    resolve(true)
                } else {
                    reject("POP_TO_ROOT_FAILED", error?.localizedDescription ?? "Unknown error", error)
                }
            })
        }
    }
    
    @objc(updateTemplate:resolver:rejecter:)
    func updateTemplate(_ templateConfig: NSDictionary,
                       resolver resolve: @escaping RCTPromiseResolveBlock,
                       rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let templateId = templateConfig["id"] as? String,
                  var template = self.templates[templateId] else {
                reject("TEMPLATE_NOT_FOUND", "Template not found", nil)
                return
            }
            
            // Update template properties based on type
            if let mapTemplate = template as? CPMapTemplate {
                self.updateMapTemplate(mapTemplate, with: templateConfig)
            } else if let listTemplate = template as? CPListTemplate {
                self.updateListTemplate(listTemplate, with: templateConfig)
            }
            
            resolve(true)
        }
    }
    
    @objc(startNavigationSession:resolver:rejecter:)
    func startNavigationSession(_ config: NSDictionary,
                               resolver resolve: @escaping RCTPromiseResolveBlock,
                               rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let rootTemplate = self.interfaceController?.rootTemplate as? CPMapTemplate else {
                reject("NO_MAP_TEMPLATE", "Root template must be a map template", nil)
                return
            }
            
            let trip = CPTrip(origin: MKMapItem(), destination: MKMapItem(), routeChoices: [])
            
            if let estimates = config["tripEstimates"] as? NSDictionary {
                let travelEstimates = CPTravelEstimates(
                    distanceRemaining: Measurement(value: estimates["distanceRemaining"] as? Double ?? 0, unit: .meters),
                    timeRemaining: estimates["timeRemaining"] as? TimeInterval ?? 0
                )
                trip.userInfo = ["estimates": travelEstimates]
            }
            
            self.navigationSession = rootTemplate.startNavigationSession(for: trip)
            resolve(true)
        }
    }
    
    @objc(endNavigationSession:rejecter:)
    func endNavigationSession(_ resolve: @escaping RCTPromiseResolveBlock,
                             rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            self.navigationSession?.finishTrip()
            self.navigationSession = nil;
            resolve(true)
        }
    }
    
    @objc(updateManeuver:resolver:rejecter:)
    func updateManeuver(_ maneuverConfig: NSDictionary,
                       resolver resolve: @escaping RCTPromiseResolveBlock,
                       rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let navigationSession = self.navigationSession else {
                reject("NO_NAVIGATION_SESSION", "No active navigation session", nil)
                return
            }
            
            let maneuver = self.createManeuver(from: maneuverConfig)
            self.currentManeuver = maneuver
            
            let travelEstimates = CPTravelEstimates(
                distanceRemaining: Measurement(value: maneuverConfig["distanceRemaining"] as? Double ?? 0, unit: .meters),
                timeRemaining: 60 // Default 1 minute
            )
            
            navigationSession.updateEstimates(travelEstimates, for: maneuver)
            navigationSession.upcomingManeuvers = [maneuver]
            
            resolve(true)
        }
    }
    
    @objc(presentNavigationAlert:resolver:rejecter:)
    func presentNavigationAlert(_ alertConfig: NSDictionary,
                               resolver resolve: @escaping RCTPromiseResolveBlock,
                               rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let rootTemplate = self.interfaceController?.rootTemplate as? CPMapTemplate else {
                reject("NO_MAP_TEMPLATE", "Root template must be a map template", nil)
                return
            }
            
            let navigationAlert = self.createNavigationAlert(from: alertConfig)
            rootTemplate.present(navigationAlert: navigationAlert, animated: true)
            
            resolve(true)
        }
    }
    
    @objc(checkConnection:rejecter:)
    func checkConnection(_ resolve: @escaping RCTPromiseResolveBlock,
                        rejecter reject: @escaping RCTPromiseRejectBlock) {
        let isConnected = CPInterfaceController.shared != nil
        resolve(["isConnected": isConnected])
    }
    
    // MARK: - Template Creation
    
    private func createTemplate(from config: NSDictionary) -> CPTemplate? {
        guard let type = config["type"] as? String,
              let id = config["id"] as? String else {
            return nil
        }
        
        var template: CPTemplate?
        
        switch type {
        case "map":
            template = createMapTemplate(from: config)
        case "list":
            template = createListTemplate(from: config)
        case "grid":
            template = createGridTemplate(from: config)
        case "nowPlaying":
            template = createNowPlayingTemplate(from: config)
        default:
            return nil
        }
        
        if let template = template {
            templates[id] = template
        }
        
        return template
    }
    
    private func createMapTemplate(from config: NSDictionary) -> CPMapTemplate {
        let mapTemplate = CPMapTemplate()
        
        if let guidanceColor = config["guidanceBackgroundColor"] as? String {
            mapTemplate.guidanceBackgroundColor = UIColor(hex: guidanceColor)
        }
        
        if let mapButtons = config["mapButtons"] as? [[String: Any]] {
            mapTemplate.mapButtons = mapButtons.compactMap { createMapButton(from: $0) }
        }
        
        mapTemplate.mapDelegate = self
        
        return mapTemplate
    }
    
    private func createListTemplate(from config: NSDictionary) -> CPListTemplate {
        let sections = (config["sections"] as? [[String: Any]] ?? []).compactMap { sectionConfig -> CPListSection? in
            let items = (sectionConfig["items"] as? [[String: Any]] ?? []).compactMap { itemConfig -> CPListItem? in
                return createListItem(from: itemConfig)
            }
            
            let section = CPListSection(items: items)
            if let header = sectionConfig["header"] as? String {
                section.header = header
            }
            
            return section
        }
        
        let listTemplate = CPListTemplate(title: config["title"] as? String ?? "", sections: sections)
        listTemplate.delegate = self
        
        return listTemplate
    }
    
    private func createGridTemplate(from config: NSDictionary) -> CPGridTemplate {
        let gridButtons = (config["buttons"] as? [[String: Any]] ?? []).compactMap { buttonConfig -> CPGridButton? in
            guard let title = buttonConfig["title"] as? String else { return nil }
            
            let button = CPGridButton(titleVariants: [title], image: UIImage(systemName: "car.fill")!) { _ in
                self.sendEvent(withName: "didSelectGridButton", body: ["title": title])
            }
            
            return button
        }
        
        return CPGridTemplate(title: config["title"] as? String ?? "", gridButtons: gridButtons)
    }
    
    private func createNowPlayingTemplate(from config: NSDictionary) -> CPNowPlayingTemplate {
        return CPNowPlayingTemplate.shared
    }
    
    private func createMapButton(from config: [String: Any]) -> CPMapButton? {
        guard let id = config["id"] as? String,
              let imageName = config["image"] as? String,
              let image = UIImage(named: imageName) else {
            return nil
        }
        
        let button = CPMapButton { _ in
            self.sendEvent(withName: self.EVENT_DID_SELECT_MAP_BUTTON, body: id)
        }
        
        button.image = image
        
        if let focusedImageName = config["focusedImage"] as? String,
           let focusedImage = UIImage(named: focusedImageName) {
            button.focusedImage = focusedImage
        }
        
        return button
    }
    
    private func createListItem(from config: [String: Any]) -> CPListItem? {
        guard let text = config["text"] as? String else { return nil }
        
        let item = CPListItem(text: text, detailText: config["detailText"] as? String)
        
        if let imageName = config["image"] as? String,
           let image = UIImage(named: imageName) {
            item.image = image
        }
        
        if let isPlaying = config["isPlaying"] as? Bool {
            item.isPlaying = isPlaying
        }
        
        if let playbackProgress = config["playbackProgress"] as? CGFloat {
            item.playbackProgress = playbackProgress
        }
        
        return item
    }
    
    private func createManeuver(from config: NSDictionary) -> CPManeuver {
        let maneuver = CPManeuver()
        
        if let symbolImageName = config["symbolImage"] as? String {
            switch symbolImageName {
            case "turn_left":
                maneuver.symbolImage = UIImage(systemName: "arrow.turn.up.left")!
            case "turn_right":
                maneuver.symbolImage = UIImage(systemName: "arrow.turn.up.right")!
            case "straight":
                maneuver.symbolImage = UIImage(systemName: "arrow.up")!
            default:
                maneuver.symbolImage = UIImage(systemName: "location.north.fill")!
            }
        }
        
        if let instruction = config["instruction"] as? String {
            maneuver.instructionVariants = [instruction]
        }
        
        if let distanceRemaining = config["distanceRemaining"] as? Double {
            maneuver.initialTravelEstimates = CPTravelEstimates(
                distanceRemaining: Measurement(value: distanceRemaining, unit: .meters),
                timeRemaining: 60
            )
        }
        
        return maneuver
    }
    
    private func createNavigationAlert(from config: NSDictionary) -> CPNavigationAlert {
        let primaryAction = CPAlertAction(
            title: (config["primaryAction"] as? NSDictionary)?["title"] as? String ?? "OK",
            style: .default
        ) { _ in
            // Handle primary action
        }
        
        var secondaryAction: CPAlertAction?
        if let secondaryConfig = config["secondaryAction"] as? NSDictionary,
           let title = secondaryConfig["title"] as? String {
            secondaryAction = CPAlertAction(title: title, style: .cancel) { _ in
                // Handle secondary action
            }
        }
        
        let navigationAlert = CPNavigationAlert(
            titleVariants: config["titleVariants"] as? [String] ?? ["Alert"],
            subtitleVariants: config["subtitleVariants"] as? [String],
            image: nil,
            primaryAction: primaryAction,
            secondaryAction: secondaryAction,
            duration: config["duration"] as? TimeInterval ?? 5.0
        )
        
        return navigationAlert
    }
    
    // MARK: - Template Updates
    
    private func updateMapTemplate(_ template: CPMapTemplate, with config: NSDictionary) {
        if let mapButtons = config["mapButtons"] as? [[String: Any]] {
            template.mapButtons = mapButtons.compactMap { createMapButton(from: $0) }
        }
        
        if let tripEstimates = config["tripEstimates"] as? NSDictionary,
           let distanceRemaining = tripEstimates["distanceRemaining"] as? Double,
           let timeRemaining = tripEstimates["timeRemaining"] as? TimeInterval {
            
            let estimates = CPTravelEstimates(
                distanceRemaining: Measurement(value: distanceRemaining, unit: .meters),
                timeRemaining: timeRemaining
            )
            
            if let currentManeuver = self.currentManeuver {
                navigationSession?.updateEstimates(estimates, for: currentManeuver)
            }
        }
    }
    
    private func updateListTemplate(_ template: CPListTemplate, with config: NSDictionary) {
        // List templates are generally immutable after creation
        // Would need to push a new template for updates
    }
    
    // MARK: - CPInterfaceControllerDelegate
    
    func templateWillAppear(_ aTemplate: CPTemplate, animated: Bool) {
        // Template will appear
    }
    
    func templateDidAppear(_ aTemplate: CPTemplate, animated: Bool) {
        // Template did appear
    }
    
    func templateWillDisappear(_ aTemplate: CPTemplate, animated: Bool) {
        // Template will disappear
    }
    
    func templateDidDisappear(_ aTemplate: CPTemplate, animated: Bool) {
        // Template did disappear
    }
    
    // MARK: - CPMapTemplateDelegate
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, panWith direction: CPMapTemplate.PanDirection) {
        // Handle pan gestures
    }
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, didBeginPanGesture gesture: UIPanGestureRecognizer) {
        // Pan gesture began
    }
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, didEndPanGestureWithVelocity velocity: CGPoint) {
        // Pan gesture ended
    }
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, willShow navigationAlert: CPNavigationAlert) {
        // Navigation alert will show
    }
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, didShow navigationAlert: CPNavigationAlert) {
        // Navigation alert did show
    }
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, willDismiss navigationAlert: CPNavigationAlert, dismissalContext: CPNavigationAlert.DismissalContext) {
        // Navigation alert will dismiss
    }
    
    func mapTemplate(_ mapTemplate: CPMapTemplate, didDismiss navigationAlert: CPNavigationAlert, dismissalContext: CPNavigationAlert.DismissalContext) {
        // Navigation alert did dismiss
    }
    
    // MARK: - CPListTemplateDelegate
    
    func listTemplate(_ listTemplate: CPListTemplate, didSelect item: CPListItem, completionHandler: @escaping () -> Void) {
        sendEvent(withName: EVENT_DID_SELECT_LIST_ITEM, body: [
            "text": item.text ?? "",
            "detailText": item.detailText ?? ""
        ])
        completionHandler()
    }
    
    // MARK: - Scene Management
    
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard scene is CPTemplateApplicationScene else { return }
        
        interfaceController = CPInterfaceController.shared
        interfaceController?.delegate = self
        
        sendEvent(withName: EVENT_DID_CONNECT, body: nil)
    }
    
    func sceneDidDisconnect(_ scene: UIScene) {
        guard scene is CPTemplateApplicationScene else { return }
        
        interfaceController = nil
        sendEvent(withName: EVENT_DID_DISCONNECT, body: nil)
    }
}

// MARK: - Extensions

extension UIColor {
    convenience init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        
        self.init(
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            alpha: Double(a) / 255
        )
    }
}
