import SwiftUI

// MARK: - Data Models

struct Employee: Codable, Identifiable {
    let id: String
    let employeeNumber: String
    let name: String
    let department: String
    let position: String
}

struct CaptureResponse: Codable {
    let success: Bool
    let applePassURL: String?
    let googlePassURL: String?
    let cardImageURL: String?
    let employee: Employee

    enum CodingKeys: String, CodingKey {
        case success
        case applePassURL = "apple_pass_url"
        case googlePassURL = "google_pass_url"
        case cardImageURL = "card_image_url"
        case employee
    }
}

struct QualityCheckResult {
    let passed: Bool
    let reason: QualityFailReason?
    let message: String?

    static let success = QualityCheckResult(passed: true, reason: nil, message: nil)

    static func failure(_ reason: QualityFailReason) -> QualityCheckResult {
        return QualityCheckResult(passed: false, reason: reason, message: reason.koreanMessage)
    }
}

enum QualityFailReason {
    case lowLight
    case notFrontal
    case faceTooSmall
    case eyesNotVisible
    case noFaceDetected

    var koreanMessage: String {
        switch self {
        case .lowLight:
            return "조금 더 밝은 곳으로 이동해주세요"
        case .notFrontal:
            return "정면을 바라봐주세요"
        case .faceTooSmall:
            return "조금 더 가까이 와주세요"
        case .eyesNotVisible:
            return "눈이 보이도록 해주세요"
        case .noFaceDetected:
            return "얼굴을 원 안에 위치시켜 주세요"
        }
    }
}

struct CardStatus: Codable, Identifiable {
    let id: String
    let status: String
    let issuedAt: String
    let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case status
        case issuedAt = "issued_at"
        case expiresAt = "expires_at"
    }
}

// MARK: - Design System

enum IDNTDesign {
    // Colors
    static let background = Color(hex: 0x000000)
    static let primary = Color(hex: 0xFFFFFF)
    static let accent = Color(hex: 0x007AFF)
    static let success = Color(hex: 0x30D158)
    static let error = Color(hex: 0xFF453A)

    // Typography
    static let mainSize: CGFloat = 28
    static let secondarySize: CGFloat = 15

    static func mainFont() -> Font {
        .system(size: mainSize, weight: .bold, design: .default)
    }

    static func secondaryFont() -> Font {
        .system(size: secondarySize, weight: .regular, design: .default)
    }

    static func displayFont(size: CGFloat = mainSize) -> Font {
        .system(size: size, weight: .bold, design: .default)
    }

    static func monoFont(size: CGFloat = secondarySize) -> Font {
        .system(size: size, weight: .regular, design: .monospaced)
    }

    // Animation
    static let springAnimation = Animation.spring(
        response: 0.5,
        dampingFraction: 1.0,
        blendDuration: 0
    )

    static let cardSpring = Animation.spring(
        response: 0.6,
        dampingFraction: 0.85,
        blendDuration: 0
    )
}

// MARK: - Color Extension

extension Color {
    init(hex: UInt, opacity: Double = 1.0) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255.0,
            green: Double((hex >> 8) & 0xFF) / 255.0,
            blue: Double(hex & 0xFF) / 255.0,
            opacity: opacity
        )
    }
}
