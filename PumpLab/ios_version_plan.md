# Plan Evaluation: iOS Version

## Executive Summary

**Impractical, Not Recommended.**

Creating a native iOS version of `pumpflow` is a strategically and technically questionable goal. The core value proposition of the application—its desktop-centric, visual dataflow paradigm—is fundamentally incompatible with the constraints of a small, touch-based mobile screen. Any attempt at a port would require a complete product redesign and a full rewrite of the UI, with a very high risk of producing a compromised and subpar user experience.

---

## Proposed Architecture: A Complete Rewrite

There is no direct path to port the existing `pumpflow` application to iOS. The PySide6/Qt stack is not a first-class citizen on mobile, and more importantly, the UI design is unsuitable. Any approach would involve a near-total rewrite.

1.  **Full Native Rewrite (Swift/SwiftUI):** This is the "correct" way to build an iOS app, but it would mean abandoning all existing `pumpflow` code. The `pump` physics library, being pure Python, could not be used directly. Its logic would have to be painstakingly translated to Swift, a massive and error-prone undertaking.

2.  **Python-on-iOS Frameworks (Kivy/BeeWare):** These frameworks allow you to package a Python interpreter and libraries into an iOS app. This would theoretically allow for the reuse of the `pump` library. However, the entire `pumpflow` UI would still need to be rewritten from scratch using the specific UI toolkit provided by the framework (e.g., Kivy's language or BeeWare's Toga). These toolkits are less mature than native or web frameworks, and managing dependencies with C extensions (like NumPy) can be brittle.

---

## Rendering Capabilities

The discussion of "rendering" for iOS highlights the fundamental problems with this approach.

### 1. Application Rendering

This is the primary obstacle. **A direct rendering of the node-graph canvas is not viable.**

*   **The Problem:** Imagine trying to accurately drag a connection from a tiny output port to a tiny input port on an iPhone screen with your finger. Or trying to read and edit the multi-field dialogs. The user experience would be frustrating and unusable.
*   **The "Solution":** To make it work, the entire UI paradigm would have to be abandoned. The application would need to be "rendered" as a completely different experience, likely a linear, multi-page wizard that guides the user step-by-step through the analysis. This sacrifices the core "visual workbench" concept that defines `pumpflow`.

### 2. Output Rendering (Reports)

Generating reports on-device would be difficult and require completely new implementations.

*   **`.docx` Reports:** The `python-docx` library and its dependencies would need to be packaged into the iOS app bundle. This can be complex and significantly increase the app's size and startup time. It's a high-risk dependency.
*   **PDF Reports:** iOS has native capabilities for creating PDFs from its UI views (`UIView`). However, this would require writing a completely new report generation engine in Swift or the chosen Python-on-iOS framework's toolkit. The existing `ReportGenerator` could not be reused.

### 3. Workflow Rendering (Canvas Export)

This feature becomes largely irrelevant. If the canvas UI is abandoned in favor of a wizard, there is no visual workflow to export. If a heavily simplified canvas is attempted, the export functionality would have to be custom-built from scratch with no reusable components.

### 4. Component Catalog Rendering

This concept does not apply in the same way. While one could take screenshots of native UI components for documentation, it's not the same as the automated, scriptable rendering possible in the web or even desktop environments.

---

## Conclusion

The iOS version is a high-risk, low-reward distraction. The project's core identity is tied to a desktop-first, expert-oriented visual paradigm. Forcing this into a mobile form factor would require sacrificing its primary strengths and investing a massive amount of effort into a new, unproven product. The return on this investment is highly questionable. Resources would be far better spent on the recommended web version, which extends the application's reach without compromising its core value.