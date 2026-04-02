import SwiftUI

struct ProcessingView: View {
    let capturedImage: UIImage
    let onComplete: (CaptureResponse) -> Void

    @State private var rotationAngle: Double = 0
    @State private var statusIndex: Int = 0
    @State private var opacity: Double = 0

    private let statusMessages = [
        "배경 제거 중...",
        "신원 확인 중...",
        "카드 생성 중..."
    ]

    private let circleSize: CGFloat = 200

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                // Captured photo with progress ring
                ZStack {
                    // Circular progress ring
                    Circle()
                        .trim(from: 0, to: 0.25)
                        .stroke(
                            IDNTDesign.primary.opacity(0.8),
                            style: StrokeStyle(lineWidth: 2, lineCap: .round)
                        )
                        .frame(width: circleSize + 16, height: circleSize + 16)
                        .rotationEffect(.degrees(rotationAngle))

                    Circle()
                        .trim(from: 0.5, to: 0.65)
                        .stroke(
                            IDNTDesign.primary.opacity(0.4),
                            style: StrokeStyle(lineWidth: 2, lineCap: .round)
                        )
                        .frame(width: circleSize + 16, height: circleSize + 16)
                        .rotationEffect(.degrees(rotationAngle))

                    // Photo circle
                    Image(uiImage: capturedImage)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(width: circleSize, height: circleSize)
                        .clipShape(Circle())
                }

                Spacer()
                    .frame(height: 80)

                // Status text
                Text(statusMessages[min(statusIndex, statusMessages.count - 1)])
                    .font(IDNTDesign.secondaryFont())
                    .foregroundStyle(IDNTDesign.primary.opacity(0.7))
                    .contentTransition(.numericText())

                Spacer()
                    .frame(height: 100)
            }
            .opacity(opacity)
        }
        .onAppear {
            withAnimation(.easeIn(duration: 0.3)) {
                opacity = 1.0
            }
            startRotation()
            startStatusCycle()
            startAPICall()
        }
    }

    private func startRotation() {
        withAnimation(
            .linear(duration: 2.0)
            .repeatForever(autoreverses: false)
        ) {
            rotationAngle = 360
        }
    }

    private func startStatusCycle() {
        for i in 1..<statusMessages.count {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 1.0) {
                withAnimation(.easeInOut(duration: 0.3)) {
                    statusIndex = i
                }
            }
        }
    }

    private func startAPICall() {
        Task {
            do {
                guard let imageData = capturedImage.jpegData(compressionQuality: 0.85) else { return }
                let response = try await NetworkService.shared.capturePhoto(
                    imageData: imageData,
                    employeeId: "demo"
                )
                // Ensure minimum display time of 3 seconds
                try await Task.sleep(for: .seconds(max(0, 3.0)))
                await MainActor.run {
                    onComplete(response)
                }
            } catch {
                // Fallback with mock data after processing animation
                try? await Task.sleep(for: .seconds(3.0))
                let mockResponse = CaptureResponse(
                    success: true,
                    applePassURL: nil,
                    googlePassURL: nil,
                    cardImageURL: nil,
                    employee: Employee(
                        id: "demo-001",
                        employeeNumber: "EMP-2026-0042",
                        name: "김아이덴",
                        department: "디자인팀",
                        position: "시니어 디자이너"
                    )
                )
                await MainActor.run {
                    onComplete(mockResponse)
                }
            }
        }
    }
}
