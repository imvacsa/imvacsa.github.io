import Foundation

// MARK: - Network Service

actor NetworkService {
    static let shared = NetworkService()

    // Base URL is configurable - change this to point to your backend
    private var baseURL: String = "https://api.idnt.app"

    private let session: URLSession
    private let decoder: JSONDecoder

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase
    }

    // MARK: - Configuration

    func setBaseURL(_ url: String) {
        self.baseURL = url
    }

    // MARK: - API: Capture Photo

    /// Uploads a captured face photo and returns card data.
    /// POST /api/v1/capture
    func capturePhoto(imageData: Data, employeeId: String) async throws -> CaptureResponse {
        let url = try buildURL(path: "/api/v1/capture")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        // Build multipart/form-data body
        let boundary = "IDNT-Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Employee ID field
        body.appendMultipartField(name: "employee_id", value: employeeId, boundary: boundary)

        // Image file field
        body.appendMultipartFile(
            name: "photo",
            filename: "capture.jpg",
            mimeType: "image/jpeg",
            data: imageData,
            boundary: boundary
        )

        // Close boundary
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.httpError(statusCode: httpResponse.statusCode, data: data)
        }

        do {
            return try decoder.decode(CaptureResponse.self, from: data)
        } catch {
            throw NetworkError.decodingFailed(underlying: error)
        }
    }

    // MARK: - API: Get Card Status

    /// Fetches the current status of an employee's digital ID card.
    /// GET /api/v1/cards/:employeeId/status
    func getCardStatus(employeeId: String) async throws -> CardStatus {
        let url = try buildURL(path: "/api/v1/cards/\(employeeId)/status")

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.httpError(statusCode: httpResponse.statusCode, data: data)
        }

        do {
            return try decoder.decode(CardStatus.self, from: data)
        } catch {
            throw NetworkError.decodingFailed(underlying: error)
        }
    }

    // MARK: - Helpers

    private func buildURL(path: String) throws -> URL {
        guard let url = URL(string: baseURL + path) else {
            throw NetworkError.invalidURL(path: path)
        }
        return url
    }
}

// MARK: - Network Errors

enum NetworkError: LocalizedError {
    case invalidURL(path: String)
    case invalidResponse
    case httpError(statusCode: Int, data: Data)
    case decodingFailed(underlying: Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL(let path):
            return "Invalid URL for path: \(path)"
        case .invalidResponse:
            return "Server returned an invalid response"
        case .httpError(let statusCode, _):
            return "HTTP error \(statusCode)"
        case .decodingFailed(let underlying):
            return "Failed to decode response: \(underlying.localizedDescription)"
        }
    }
}

// MARK: - Data Extensions for Multipart

private extension Data {
    mutating func appendMultipartField(name: String, value: String, boundary: String) {
        let field = "--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n"
        if let data = field.data(using: .utf8) {
            append(data)
        }
    }

    mutating func appendMultipartFile(name: String, filename: String, mimeType: String, data: Data, boundary: String) {
        let header = "--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"; filename=\"\(filename)\"\r\nContent-Type: \(mimeType)\r\n\r\n"
        if let headerData = header.data(using: .utf8) {
            append(headerData)
        }
        append(data)
        if let lineBreak = "\r\n".data(using: .utf8) {
            append(lineBreak)
        }
    }
}
