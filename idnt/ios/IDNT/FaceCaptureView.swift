import SwiftUI
import AVFoundation
import Vision

// MARK: - Camera Preview UIViewRepresentable

struct CameraPreviewLayer: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        context.coordinator.previewLayer = previewLayer
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        DispatchQueue.main.async {
            context.coordinator.previewLayer?.frame = uiView.bounds
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator {
        var previewLayer: AVCaptureVideoPreviewLayer?
    }
}

// MARK: - Camera Manager

@MainActor
class CameraManager: NSObject, ObservableObject {
    let session = AVCaptureSession()
    private let videoOutput = AVCaptureVideoDataOutput()
    private let processingQueue = DispatchQueue(label: "com.idnt.camera", qos: .userInteractive)

    @Published var qualityResult: QualityCheckResult = .failure(.noFaceDetected)
    @Published var capturedImage: UIImage?
    @Published var isCaptured: Bool = false

    private var lastProcessTime: Date = .distantPast
    private let processInterval: TimeInterval = 1.0 / 60.0 // 60fps processing
    private var isCapturing = false

    func startSession() {
        guard !session.isRunning else { return }

        session.sessionPreset = .high

        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front),
              let input = try? AVCaptureDeviceInput(device: camera) else { return }

        if session.canAddInput(input) {
            session.addInput(input)
        }

        videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
        videoOutput.alwaysDiscardsLateVideoFrames = true

        if session.canAddOutput(videoOutput) {
            session.addOutput(videoOutput)
        }

        if let connection = videoOutput.connection(with: .video) {
            connection.isVideoMirrored = true
        }

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.session.startRunning()
        }
    }

    func stopSession() {
        guard session.isRunning else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.session.stopRunning()
        }
    }

    private func captureImage(from sampleBuffer: CMSampleBuffer) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        let image = UIImage(cgImage: cgImage)
        Task { @MainActor in
            self.capturedImage = image
            self.isCaptured = true
        }
    }

    fileprivate func processFrame(_ sampleBuffer: CMSampleBuffer) {
        let now = Date()
        guard now.timeIntervalSince(lastProcessTime) >= processInterval else { return }
        lastProcessTime = now
        guard !isCapturing else { return }

        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        let request = VNDetectFaceLandmarksRequest { [weak self] request, error in
            guard let self = self, error == nil else { return }

            guard let results = request.results as? [VNFaceObservation],
                  let face = results.first else {
                Task { @MainActor in
                    self.qualityResult = .failure(.noFaceDetected)
                }
                return
            }

            let imageSize = CGSize(
                width: CGFloat(CVPixelBufferGetWidth(pixelBuffer)),
                height: CGFloat(CVPixelBufferGetHeight(pixelBuffer))
            )
            let result = self.evaluateQuality(face: face, imageSize: imageSize)

            Task { @MainActor in
                self.qualityResult = result

                if result.passed && !self.isCapturing {
                    self.isCapturing = true
                    self.captureImage(from: sampleBuffer)
                }
            }
        }

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .leftMirrored, options: [:])
        try? handler.perform([request])
    }

    private func evaluateQuality(face: VNFaceObservation, imageSize: CGSize) -> QualityCheckResult {
        // Check face size (face bounding box area relative to frame)
        let faceArea = face.boundingBox.width * face.boundingBox.height
        let frameArea = imageSize.width * imageSize.height
        let facePixelArea = faceArea * frameArea
        let threshold: CGFloat = 300 * 300

        guard facePixelArea > threshold else {
            return .failure(.faceTooSmall)
        }

        // Check frontal pose: yaw within +/-15 degrees
        if let yaw = face.yaw?.doubleValue {
            let yawDegrees = yaw * 180.0 / .pi
            guard abs(yawDegrees) <= 15 else {
                return .failure(.notFrontal)
            }
        }

        // Check frontal pose: pitch within +/-15 degrees
        if let pitch = face.pitch?.doubleValue {
            let pitchDegrees = pitch * 180.0 / .pi
            guard abs(pitchDegrees) <= 15 else {
                return .failure(.notFrontal)
            }
        }

        // Check eye detection (both eyes must be visible)
        if let landmarks = face.landmarks {
            guard landmarks.leftEye != nil, landmarks.rightEye != nil else {
                return .failure(.eyesNotVisible)
            }
        } else {
            return .failure(.eyesNotVisible)
        }

        return .success
    }
}

extension CameraManager: AVCaptureVideoDataOutputSampleBufferDelegate {
    nonisolated func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        let manager = self
        manager.processFrame(sampleBuffer)
    }
}

// MARK: - Face Capture View

struct FaceCaptureView: View {
    let onCapture: (UIImage) -> Void

    @StateObject private var cameraManager = CameraManager()
    @State private var pulseScale: CGFloat = 1.0
    @State private var hasNavigated = false

    private let circleSize: CGFloat = 280

    private var frameColor: Color {
        if cameraManager.qualityResult.passed {
            return IDNTDesign.success
        } else if cameraManager.qualityResult.reason == .noFaceDetected {
            return .white
        } else {
            return IDNTDesign.error
        }
    }

    private var statusText: String {
        cameraManager.qualityResult.message ?? "얼굴을 원 안에 위치시켜 주세요"
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            CameraPreviewLayer(session: cameraManager.session)
                .ignoresSafeArea()
                .opacity(0.7)

            // Dimming overlay with circular cutout
            Canvas { context, size in
                let rect = CGRect(origin: .zero, size: size)
                let circleRect = CGRect(
                    x: (size.width - circleSize) / 2,
                    y: (size.height - circleSize) / 2 - 40,
                    width: circleSize,
                    height: circleSize
                )
                var path = Path(rect)
                path.addEllipse(in: circleRect)
                context.fill(path, with: .color(.black.opacity(0.6)), style: FillStyle(eoFill: true))
            }
            .ignoresSafeArea()
            .allowsHitTesting(false)

            VStack(spacing: 0) {
                Spacer()

                // Pulsating circle frame with spring-based breathing animation
                Circle()
                    .strokeBorder(frameColor, lineWidth: 3)
                    .frame(width: circleSize, height: circleSize)
                    .scaleEffect(pulseScale)
                    .animation(IDNTDesign.springAnimation, value: frameColor)

                Spacer()
                    .frame(height: 60)

                // Status text (single line)
                Text(statusText)
                    .font(IDNTDesign.secondaryFont())
                    .foregroundStyle(frameColor)
                    .multilineTextAlignment(.center)
                    .lineLimit(1)
                    .animation(IDNTDesign.springAnimation, value: statusText)

                Spacer()
                    .frame(height: 80)
            }
        }
        .onAppear {
            cameraManager.startSession()
            startBreathingAnimation()
        }
        .onDisappear {
            cameraManager.stopSession()
        }
        .onChange(of: cameraManager.isCaptured) { _, captured in
            if captured, let image = cameraManager.capturedImage, !hasNavigated {
                hasNavigated = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    cameraManager.stopSession()
                    onCapture(image)
                }
            }
        }
    }

    private func startBreathingAnimation() {
        // Soft breathing animation using spring physics
        withAnimation(
            .spring(response: 1.5, dampingFraction: 0.5)
            .repeatForever(autoreverses: true)
        ) {
            pulseScale = 1.03
        }
    }
}
