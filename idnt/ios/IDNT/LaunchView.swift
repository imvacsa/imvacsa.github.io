import SwiftUI

struct LaunchView: View {
    let onComplete: () -> Void

    @State private var opacity: Double = 0.0

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            Text("IDNT")
                .font(.system(size: 48, weight: .bold, design: .default))
                .foregroundStyle(.white)
                .opacity(opacity)
        }
        .onAppear {
            withAnimation(.easeIn(duration: 0.3)) {
                opacity = 1.0
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                onComplete()
            }
        }
    }
}
