import AppKit
import Foundation
import Vision

struct TextRegion: Codable {
    let text: String
    let confidence: Float
    let bbox: [Double]
}

struct OCRResult: Codable {
    let image: String
    let width: Double
    let height: Double
    let regions: [TextRegion]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

guard CommandLine.arguments.count >= 3 else {
    fail("Usage: swift vision_ocr.swift <image.png> <output.json>")
}

let imagePath = CommandLine.arguments[1]
let outputPath = CommandLine.arguments[2]
let imageURL = URL(fileURLWithPath: imagePath)

guard let nsImage = NSImage(contentsOf: imageURL) else {
    fail("Could not open image: \(imagePath)")
}

var proposedRect = CGRect(origin: .zero, size: nsImage.size)
guard let cgImage = nsImage.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil) else {
    fail("Could not create CGImage: \(imagePath)")
}

let imageWidth = Double(cgImage.width)
let imageHeight = Double(cgImage.height)
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["zh-Hans", "en-US"]

do {
    try handler.perform([request])
} catch {
    fail("Vision OCR failed: \(error)")
}

let observations = request.results ?? []
let regions: [TextRegion] = observations.compactMap { obs in
    guard let candidate = obs.topCandidates(1).first else { return nil }
    let box = obs.boundingBox
    let x0 = Double(box.minX) * imageWidth
    let y0 = (1.0 - Double(box.maxY)) * imageHeight
    let x1 = Double(box.maxX) * imageWidth
    let y1 = (1.0 - Double(box.minY)) * imageHeight
    return TextRegion(
        text: candidate.string,
        confidence: candidate.confidence,
        bbox: [x0, y0, x1, y1]
    )
}

let result = OCRResult(
    image: imagePath,
    width: imageWidth,
    height: imageHeight,
    regions: regions
)

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
let data = try encoder.encode(result)
try data.write(to: URL(fileURLWithPath: outputPath))
print("OCR \(URL(fileURLWithPath: imagePath).lastPathComponent): \(regions.count) regions")
