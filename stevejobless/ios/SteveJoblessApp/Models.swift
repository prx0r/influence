import Foundation

struct StudioProject: Codable, Identifiable {
    let id: Int
    let slug: String
    let name: String
    let domain: String?
    let progress: Int
    let resources: [StudioResource]
    let actions: [StudioAction]
}

struct StudioResource: Codable, Identifiable {
    var id: String { key }
    let key: String
    let kind: String
    let label: String
    let status: String
    let message: String?
    let executor: String
}

struct StudioAction: Codable, Identifiable {
    let id: Int
    let resourceKey: String
    let title: String
    let instructions: String
    let url: String?
    let estimateSeconds: Int
    let priority: Int
    let done: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, instructions, url, priority, done
        case resourceKey = "resource_key"
        case estimateSeconds = "estimate_seconds"
    }
}
