/**
 * Workspace Layout - Bypasses default app shell
 *
 * The workspace has its own sidebar and layout, so we don't need
 * the default AppHeader.
 */

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
