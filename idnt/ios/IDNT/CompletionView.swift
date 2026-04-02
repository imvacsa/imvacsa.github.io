import SwiftUI
import PassKit

// MARK: - Completion View (Screen 3)

struct CompletionView: View {
    let captureResponse: CaptureResponse

    @State private var isFlipped: Bool = false
    @State private var cardOffset: CGFloat = -600
    @State private var cardRotationX: Double = -30
    @State private var cardRotationY: Double = 15
    @State private var showButton: Bool = false
    @State private var showCompletion: Bool = false
    @State private var checkmarkScale: CGFloat = 0
    @State private var showPassKit: Bool = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                // 3D animated ID card
                IDCardView(
                    employee: captureResponse.employee,
                    photo: nil, // Photo would come from captured image in real flow
                    isFlipped: isFlipped
                )
                .padding(.horizontal, 32)
                .rotation3DEffect(
                    .degrees(isFlipped ? 180 : 0),
                    axis: (x: 0, y: 1, z: 0),
                    perspective: 0.5
                )
                .rotation3DEffect(
                    .degrees(cardRotationX),
                    axis: (x: 1, y: 0, z: 0),
                    perspective: 0.5
                )
                .rotation3DEffect(
                    .degrees(cardRotationY),
                    axis: (x: 0, y: 1, z: 0),
                    perspective: 0.5
                )
                .offset(y: cardOffset)
                .onTapGesture {
                    guard !showCompletion else { return }
                    withAnimation(IDNTDesign.cardSpring) {
                        isFlipped.toggle()
                    }
                }

                Spacer()

                // Completion state
                if showCompletion {
                    VStack(spacing: 16) {
                        // Checkmark animation
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 48, weight: .light))
                            .foregroundStyle(IDNTDesign.success)
                            .scaleEffect(checkmarkScale)

                        Text("완료. 출입문을 태그해보세요.")
                            .font(IDNTDesign.secondaryFont())
                            .foregroundStyle(IDNTDesign.primary.opacity(0.7))
                    }
                    .padding(.bottom, 60)
                    .transition(.opacity)
                }

                // Add to Wallet button (single button per screen)
                if showButton && !showCompletion {
                    Button(action: {
                        addToWallet()
                    }) {
                        HStack(spacing: 8) {
                            Image(systemName: "wallet.pass")
                                .font(.system(size: 18, weight: .medium))
                            Text("지갑에 추가")
                                .font(.system(size: 17, weight: .semibold))
                        }
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 54)
                        .background(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(IDNTDesign.accent)
                        )
                    }
                    .padding(.horizontal, 32)
                    .padding(.bottom, 48)
                    .transition(.opacity)
                }
            }
        }
        .onAppear {
            animateCardEntrance()
        }
        .sheet(isPresented: $showPassKit) {
            PassKitSheet(passURL: captureResponse.applePassURL) {
                showPassKit = false
                showCompletionState()
            }
        }
    }

    // MARK: - Animations

    private func animateCardEntrance() {
        // Card drops in with spring physics and tilted perspective
        withAnimation(.spring(response: 0.8, dampingFraction: 0.75)) {
            cardOffset = 0
        }

        // Settle the 3D rotation to flat
        withAnimation(.spring(response: 1.0, dampingFraction: 0.8).delay(0.3)) {
            cardRotationX = 0
            cardRotationY = 0
        }

        // Show button after card settles
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            withAnimation(IDNTDesign.springAnimation) {
                showButton = true
            }
        }
    }

    private func addToWallet() {
        if captureResponse.applePassURL != nil {
            showPassKit = true
        } else {
            // No pass URL available, show completion directly
            showCompletionState()
        }
    }

    private func showCompletionState() {
        withAnimation(IDNTDesign.springAnimation) {
            showButton = false
            showCompletion = true
        }

        // Checkmark scale-in animation
        withAnimation(.spring(response: 0.5, dampingFraction: 0.6).delay(0.2)) {
            checkmarkScale = 1.0
        }
    }
}

// MARK: - PassKit Sheet (PKAddPassesViewController wrapper)

struct PassKitSheet: UIViewControllerRepresentable {
    let passURL: String?
    let onDismiss: () -> Void

    func makeUIViewController(context: Context) -> UIViewController {
        let controller = UIViewController()
        controller.view.backgroundColor = .clear

        guard let urlString = passURL,
              let url = URL(string: urlString) else {
            // If no valid URL, dismiss immediately
            DispatchQueue.main.async {
                onDismiss()
            }
            return controller
        }

        // Download and present the pass
        Task {
            do {
                let (data, _) = try await URLSession.shared.data(from: url)
                var loadError: NSError?
                let pass = PKPass(data: data, error: &loadError)

                guard loadError == nil else {
                    await MainActor.run { onDismiss() }
                    return
                }

                await MainActor.run {
                    guard let addPassVC = PKAddPassesViewController(pass: pass) else {
                        onDismiss()
                        return
                    }
                    addPassVC.delegate = context.coordinator
                    controller.present(addPassVC, animated: true)
                }
            } catch {
                await MainActor.run { onDismiss() }
            }
        }

        return controller
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onDismiss: onDismiss)
    }

    class Coordinator: NSObject, PKAddPassesViewControllerDelegate {
        let onDismiss: () -> Void

        init(onDismiss: @escaping () -> Void) {
            self.onDismiss = onDismiss
        }

        func addPassesViewControllerDidFinish(_ controller: PKAddPassesViewController) {
            controller.dismiss(animated: true) { [weak self] in
                self?.onDismiss()
            }
        }
    }
}
