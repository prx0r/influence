# iOS approval remote

This folder contains a minimal SwiftUI client for the SteveJobless REST API. Create a new iOS app target in Xcode and add the four Swift files.

For simulator development the API defaults to `http://127.0.0.1:8787`. For a physical iPhone, change `baseURL` to your Mac/VPS address and use HTTPS before real credentials are involved.

The native client intentionally stays thin: the backend owns studio truth, connectors and audit history; the phone is an approval/action remote.
