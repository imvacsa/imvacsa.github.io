// IDNT (아이덴트) - Digital ID Card App
//
// Build & Run Instructions:
// ==========================
// Requirements:
//   - Xcode 15.0 or later
//   - iOS 17.0+ deployment target
//   - Physical iOS device recommended (camera, NFC, Wallet features)
//
// Setup:
//   1. Open IDNT.xcodeproj (or create a new Xcode project and add these files)
//   2. Set deployment target to iOS 17.0+
//   3. Add Pretendard font files (.otf or .ttf) to the project bundle:
//      - Pretendard-Regular, Pretendard-Bold, Pretendard-Medium, Pretendard-SemiBold
//      - Register them in Info.plist under "Fonts provided by application"
//   4. Add the following to Info.plist:
//      - NSCameraUsageDescription: "IDNT needs camera access to capture your ID photo."
//      - NFCReaderUsageDescription: "IDNT uses NFC to verify your ID card."
//   5. In Signing & Capabilities, add:
//      - Wallet (PassKit) capability
//      - NFC Tag Reading capability (optional)
//   6. Select a physical device as the run destination
//   7. Build and Run (Cmd+R)
//
// Notes:
//   - Camera and NFC will not work in the iOS Simulator
//   - The app uses AVFoundation and Vision frameworks (linked automatically)
//   - PassKit framework is required for the "Add to Wallet" feature

import SwiftUI
import CoreText

@main
struct IDNTApp: App {
    init() {
        registerPretendardFonts()
    }

    var body: some Scene {
        WindowGroup {
            ContentFlowView()
                .preferredColorScheme(.dark)
        }
    }

    private func registerPretendardFonts() {
        let fontNames = [
            "Pretendard-Regular",
            "Pretendard-Bold",
            "Pretendard-Medium",
            "Pretendard-SemiBold"
        ]
        let extensions = ["otf", "ttf"]

        for fontName in fontNames {
            for ext in extensions {
                if let url = Bundle.main.url(forResource: fontName, withExtension: ext) {
                    var errorRef: Unmanaged<CFError>?
                    CTFontManagerRegisterFontsForURL(url as CFURL, .process, &errorRef)
                }
            }
        }
    }
}

// MARK: - Navigation Flow

enum AppScreen {
    case launch
    case faceCapture
    case processing(UIImage)
    case completion(CaptureResponse)
}

struct ContentFlowView: View {
    @State private var currentScreen: AppScreen = .launch

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch currentScreen {
            case .launch:
                LaunchView {
                    withAnimation(IDNTDesign.springAnimation) {
                        currentScreen = .faceCapture
                    }
                }
                .transition(.opacity)

            case .faceCapture:
                FaceCaptureView { capturedImage in
                    withAnimation(IDNTDesign.springAnimation) {
                        currentScreen = .processing(capturedImage)
                    }
                }
                .transition(.opacity)

            case .processing(let image):
                ProcessingView(capturedImage: image) { response in
                    withAnimation(IDNTDesign.springAnimation) {
                        currentScreen = .completion(response)
                    }
                }
                .transition(.opacity)

            case .completion(let response):
                CompletionView(captureResponse: response)
                    .transition(.opacity)
            }
        }
        .animation(IDNTDesign.springAnimation, value: screenIndex)
    }

    private var screenIndex: Int {
        switch currentScreen {
        case .launch: return 0
        case .faceCapture: return 1
        case .processing: return 2
        case .completion: return 3
        }
    }
}
