import SwiftUI
import CoreImage.CIFilterBuiltins

// MARK: - ID Card View (Reusable Component)

struct IDCardView: View {
    let employee: Employee
    let photo: UIImage?
    let isFlipped: Bool

    // Credit card ratio: 85.6mm x 53.98mm (approximately 1.586:1)
    private let cardRatio: CGFloat = 85.6 / 53.98

    @State private var qrFullOpacity: Bool = false

    var body: some View {
        GeometryReader { geo in
            let width = geo.size.width
            let height = width / cardRatio

            ZStack {
                if isFlipped {
                    cardBack(width: width, height: height)
                        .rotation3DEffect(.degrees(180), axis: (x: 0, y: 1, z: 0))
                } else {
                    cardFront(width: width, height: height)
                }
            }
            .frame(width: width, height: height)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
        .aspectRatio(85.6 / 53.98, contentMode: .fit)
    }

    // MARK: - Card Front

    @ViewBuilder
    private func cardFront(width: CGFloat, height: CGFloat) -> some View {
        ZStack {
            // Black matte background with subtle gradient
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(hex: 0x1A1A1A),
                            Color(hex: 0x0D0D0D),
                            Color(hex: 0x000000)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            // Subtle border
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)

            VStack(alignment: .leading, spacing: 0) {
                // Top-left: company logo (embossed look)
                HStack {
                    Text("IDNT")
                        .font(.system(size: 18, weight: .bold, design: .default))
                        .foregroundStyle(Color.white.opacity(0.3))
                        .shadow(color: .black, radius: 1, x: 0, y: 1)

                    Spacer()
                }
                .padding(.top, 20)
                .padding(.horizontal, 24)

                Spacer()

                // Center content: photo left, info right
                HStack(alignment: .center, spacing: 16) {
                    // Circular photo (left side)
                    if let photo = photo {
                        Image(uiImage: photo)
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 72, height: 72)
                            .clipShape(Circle())
                            .overlay(Circle().stroke(Color.white.opacity(0.15), lineWidth: 1))
                    } else {
                        Circle()
                            .fill(Color.white.opacity(0.1))
                            .frame(width: 72, height: 72)
                            .overlay(
                                Image(systemName: "person.fill")
                                    .foregroundStyle(Color.white.opacity(0.3))
                                    .font(.system(size: 28))
                            )
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        // Name: large white text
                        Text(employee.name)
                            .font(.system(size: 22, weight: .bold))
                            .foregroundStyle(.white)

                        // Position: smaller gray text
                        Text(employee.position)
                            .font(.system(size: 13, weight: .regular))
                            .foregroundStyle(Color.white.opacity(0.5))

                        // Department
                        Text(employee.department)
                            .font(.system(size: 11, weight: .regular))
                            .foregroundStyle(Color.white.opacity(0.35))
                    }

                    Spacer()
                }
                .padding(.horizontal, 24)

                Spacer()

                // Bottom row
                HStack(alignment: .bottom) {
                    // Employee ID: monospace, laser-engraved style
                    Text(employee.employeeNumber)
                        .font(.system(size: 11, weight: .regular, design: .monospaced))
                        .foregroundStyle(Color.white.opacity(0.25))
                        .tracking(1.5)

                    Spacer()

                    // QR code: bottom-right, 50% opacity (tap to full)
                    if let qrImage = generateQRCode(from: employee.employeeNumber) {
                        Image(uiImage: qrImage)
                            .interpolation(.none)
                            .resizable()
                            .frame(width: 44, height: 44)
                            .opacity(qrFullOpacity ? 1.0 : 0.5)
                            .onTapGesture {
                                withAnimation(IDNTDesign.springAnimation) {
                                    qrFullOpacity.toggle()
                                }
                            }
                    }
                }
                .padding(.bottom, 20)
                .padding(.horizontal, 24)
            }
        }
    }

    // MARK: - Card Back

    @ViewBuilder
    private func cardBack(width: CGFloat, height: CGFloat) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(hex: 0x0D0D0D),
                            Color(hex: 0x1A1A1A),
                            Color(hex: 0x0D0D0D)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)

            VStack(spacing: 0) {
                // Magnetic stripe
                Rectangle()
                    .fill(Color.white.opacity(0.06))
                    .frame(height: 36)
                    .padding(.top, 24)

                Spacer()

                // NFC icon
                Image(systemName: "wave.3.right")
                    .font(.system(size: 32, weight: .light))
                    .foregroundStyle(Color.white.opacity(0.3))

                Spacer()
                    .frame(height: 12)

                Text("NFC 태그 가능")
                    .font(.system(size: 11, weight: .regular))
                    .foregroundStyle(Color.white.opacity(0.25))

                Spacer()

                // Bottom info: expiry date + barcode
                HStack {
                    // Expiry: bottom-left MM/YY
                    VStack(alignment: .leading, spacing: 2) {
                        Text("VALID THRU")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(Color.white.opacity(0.2))
                        Text("12/27")
                            .font(.system(size: 14, weight: .regular, design: .monospaced))
                            .foregroundStyle(Color.white.opacity(0.4))
                    }

                    Spacer()

                    // Barcode
                    HStack(spacing: 1) {
                        ForEach(0..<30, id: \.self) { i in
                            Rectangle()
                                .fill(Color.white.opacity(i % 3 == 0 ? 0.4 : 0.15))
                                .frame(width: i % 2 == 0 ? 2 : 1, height: 28)
                        }
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
        }
    }

    // MARK: - QR Code Generator

    private func generateQRCode(from string: String) -> UIImage? {
        let context = CIContext()
        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(string.utf8)
        filter.correctionLevel = "M"

        guard let outputImage = filter.outputImage else { return nil }

        let transform = CGAffineTransform(scaleX: 10, y: 10)
        let scaledImage = outputImage.transformed(by: transform)

        // Invert colors for dark theme (white QR on transparent background)
        guard let invertFilter = CIFilter(name: "CIColorInvert") else {
            guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else { return nil }
            return UIImage(cgImage: cgImage)
        }
        invertFilter.setValue(scaledImage, forKey: kCIInputImageKey)

        guard let invertedImage = invertFilter.outputImage,
              let cgImage = context.createCGImage(invertedImage, from: invertedImage.extent) else {
            guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else { return nil }
            return UIImage(cgImage: cgImage)
        }

        return UIImage(cgImage: cgImage)
    }
}
