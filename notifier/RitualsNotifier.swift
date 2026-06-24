// Rituals notifier — a tiny signed agent that posts a macOS notification via the
// modern UserNotifications framework (UNUserNotificationCenter), so the banner is
// branded "Rituals" with the Rituals icon and the text renders reliably on current
// macOS. This replaces terminal-notifier 2.0.0, whose deprecated NSUserNotification
// path delivers empty (textless) banners on macOS 11+.
//
// It bootstraps a real (accessory) NSApplication — UNUserNotificationCenter only
// connects to the notification server from a genuine app process, not a bare CLI.
//
// Usage (run the binary inside the .app bundle so Bundle.main resolves):
//   RitualsNotifier "<title>" "<message>"   -> posts the notification
// Launched with no payload (macOS relaunching us because the banner was clicked)
//   -> opens the main Rituals app (bundle id "Rituals").

import Foundation
import UserNotifications
import AppKit

func openRitualsApp() {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: "/usr/bin/open")
    p.arguments = ["-b", "Rituals"]   // open the main app by bundle identifier
    try? p.run()
}

final class AppDelegate: NSObject, NSApplicationDelegate, UNUserNotificationCenterDelegate {
    func applicationDidFinishLaunching(_ note: Notification) {
        let center = UNUserNotificationCenter.current()
        center.delegate = self

        // Payload arrives as two trailing arguments. Ignore any LaunchServices
        // bookkeeping args (e.g. -psn_…). No payload => we were relaunched by a
        // banner click; just wait for didReceive to open the app.
        let extras = CommandLine.arguments.dropFirst().filter { !$0.hasPrefix("-") }
        if extras.count >= 2 {
            let title = extras[extras.index(extras.startIndex, offsetBy: 0)]
            let body = extras[extras.index(extras.startIndex, offsetBy: 1)]
            center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
                guard granted else {
                    DispatchQueue.main.async { NSApp.terminate(nil) }
                    return
                }
                let content = UNMutableNotificationContent()
                content.title = title
                content.body = body
                content.sound = .default
                let req = UNNotificationRequest(identifier: UUID().uuidString,
                                                content: content, trigger: nil)
                center.add(req) { _ in }
            }
        }

        // Safety net: never linger. Posting is near-instant; a click is delivered
        // to didReceive well within this window.
        DispatchQueue.main.asyncAfter(deadline: .now() + 8) { NSApp.terminate(nil) }
    }

    // Show the banner even though we (the agent) are technically the active app.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound])
    }

    // User clicked the banner -> bring the main Rituals app forward, then quit.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        openRitualsApp()
        completionHandler()
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)   // no Dock icon, no menu bar
app.run()
