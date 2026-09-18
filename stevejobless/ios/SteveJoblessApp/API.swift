import Foundation

@MainActor
final class SteveAPI: ObservableObject {
    @Published var projects: [StudioProject] = []
    @Published var isRunning = false
    @Published var error: String?

    var baseURL = URL(string: "http://127.0.0.1:8787")!

    func load() async {
        do {
            let (data, _) = try await URLSession.shared.data(from: baseURL.appending(path: "api/projects"))
            projects = try JSONDecoder().decode([StudioProject].self, from: data)
        } catch { self.error = error.localizedDescription }
    }

    func reconcileAll() async {
        isRunning = true; defer { isRunning = false }
        var request = URLRequest(url: baseURL.appending(path: "api/reconcile"))
        request.httpMethod = "POST"
        do { _ = try await URLSession.shared.data(for: request); await load() }
        catch { self.error = error.localizedDescription }
    }
}
