import { PageCustomizationProvider } from "@/context/PageCustomizationContext";
import WorkspaceSidebar from "@/components/sidebar/WorkspaceSidebar";
import AppShell from "@/components/layout/AppShell";
import { LayoutPageBar } from "@/features/ui-layout/slots";
import { CapabilityAccessProvider } from "@/components/access/CapabilityAccessContext";
import CapabilityGate from "@/components/access/CapabilityGate";
import { ChatRuntimeProvider } from "@/features/chat";
import { ReadingProvider } from "@/context/ReadingContext";
import { Suspense } from "react";
import { WorkspaceRuntimeBoundary } from "@/components/workspaces/WorkspaceRuntimeBoundary";

// Mastery-only: the calendar runtime and the settings return tracker were
// removed with their features. The shared chat viewer contexts stay because
// AssistantResponse reads them even on a mastery turn.
export default function WorkspaceLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <CapabilityAccessProvider>
      <PageCustomizationProvider>
        <Suspense>
          <WorkspaceRuntimeBoundary>
            {/* Mastery-only: no task-board runtime (it polls a deleted API). */}
            <ChatRuntimeProvider>
              <ReadingProvider>
                <AppShell sidebar={<WorkspaceSidebar />} pageBar={<LayoutPageBar />}>
                  <CapabilityGate>{children}</CapabilityGate>
                </AppShell>
              </ReadingProvider>
            </ChatRuntimeProvider>
          </WorkspaceRuntimeBoundary>
        </Suspense>
      </PageCustomizationProvider>
    </CapabilityAccessProvider>
  );
}
