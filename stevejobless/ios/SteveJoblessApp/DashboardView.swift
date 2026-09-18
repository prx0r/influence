import SwiftUI

struct DashboardView: View {
    @StateObject private var api = SteveAPI()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 14) {
                    ForEach(api.projects) { project in
                        VStack(alignment: .leading, spacing: 12) {
                            HStack(alignment: .top) {
                                VStack(alignment: .leading) {
                                    Text(project.domain ?? "NO DOMAIN").font(.caption).foregroundStyle(.secondary)
                                    Text(project.name).font(.title2.bold())
                                }
                                Spacer()
                                Text("\(project.progress)%").font(.title2.bold())
                            }
                            ProgressView(value: Double(project.progress), total: 100)
                            if let action = project.actions.first {
                                VStack(alignment: .leading, spacing: 5) {
                                    Text("NEEDS YOU").font(.caption2.bold()).foregroundStyle(.secondary)
                                    Text(action.title).font(.headline)
                                    Text(action.instructions).font(.caption).foregroundStyle(.secondary).lineLimit(3)
                                    if let s = action.url, let url = URL(string: s) {
                                        Link("DO IT", destination: url).buttonStyle(.borderedProminent)
                                    }
                                }
                                .padding().background(.thinMaterial, in: RoundedRectangle(cornerRadius: 14))
                            } else {
                                Text("No human action required").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        .padding()
                        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 20))
                    }
                }.padding()
            }
            .navigationTitle("SteveJobless")
            .toolbar { Button(api.isRunning ? "Checking…" : "Run Steve") { Task { await api.reconcileAll() } }.disabled(api.isRunning) }
            .task { await api.load() }
        }
    }
}
