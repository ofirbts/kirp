"use client";

import React, { useState, useEffect, useCallback, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DataTable } from "@/components/dashboard/DataTable";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { useCan } from "@/lib/auth/permissions";
import { apiClient } from "@/lib/apiClient";
import type { User, Role } from "@/lib/types";

function UsersRolesContent() {
  const { can } = useCan();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [userDrawerOpen, setUserDrawerOpen] = useState(false);
  const [roleDrawerOpen, setRoleDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [uRes, rRes] = await Promise.all([
        apiClient.listUsers(),
        apiClient.listRoles(),
      ]);
      setUsers((uRes.data ?? []) as User[]);
      setRoles((rRes.data ?? []) as Role[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users/roles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && users.length === 0 && roles.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Users & Roles</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Directory and permissions. Data from /api/users and /api/roles.
        </p>
      </div>

      <DataTable<User>
        title="Users"
        data={users}
        keyExtractor={(r) => r.id}
        columns={[
          { key: "name", header: "Name", render: (r) => r.name },
          { key: "email", header: "Email", render: (r) => r.email },
          { key: "status", header: "Status", render: (r) => r.status },
        ]}
        loading={loading}
        error={error}
        onRetry={load}
        emptyMessage="No users."
        pageSize={10}
        onRowClick={(row) => {
          setSelectedUser(row);
          setUserDrawerOpen(true);
        }}
      />

      <DataTable<Role>
        title="Roles"
        data={roles}
        keyExtractor={(r) => r.id}
        columns={[
          { key: "name", header: "Name", render: (r) => r.name },
          { key: "description", header: "Description", render: (r) => r.description ?? "—" },
        ]}
        loading={loading}
        error={error}
        onRetry={load}
        emptyMessage="No roles."
        pageSize={10}
        onRowClick={(row) => {
          setSelectedRole(row);
          setRoleDrawerOpen(true);
        }}
      />

      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Effective permissions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500">
            Using client-side permissions helper. Read-only until RBAC is wired.
          </p>
          <p className="mt-2 text-xs text-neutral-400">
            can("agents", "read"): {can("agents", "read") ? "yes" : "no"} · can("agents", "write"): {can("agents", "write") ? "yes" : "no"}
          </p>
        </CardContent>
      </Card>

      <Sheet open={userDrawerOpen} onOpenChange={setUserDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md border-neutral-800 bg-neutral-950">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-neutral-100">
              User details
            </SheetTitle>
          </SheetHeader>
          {selectedUser && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-neutral-500">ID</p>
                <p className="font-mono text-xs text-neutral-300">{selectedUser.id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Name / Email</p>
                <p className="text-neutral-200">{selectedUser.name} · {selectedUser.email}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Status</p>
                <p className="text-neutral-300">{selectedUser.status}</p>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Sheet open={roleDrawerOpen} onOpenChange={setRoleDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md border-neutral-800 bg-neutral-950">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-neutral-100">
              Role details
            </SheetTitle>
          </SheetHeader>
          {selectedRole && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-neutral-500">ID</p>
                <p className="font-mono text-xs text-neutral-300">{selectedRole.id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Name</p>
                <p className="text-neutral-200">{selectedRole.name}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Description</p>
                <p className="text-neutral-400">{selectedRole.description ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Permissions</p>
                <pre className="max-h-32 overflow-auto rounded bg-neutral-900 p-2 text-xs text-neutral-400">
                  {JSON.stringify(selectedRole.permissions ?? [], null, 2)}
                </pre>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export default function SettingsUsersRolesPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <UsersRolesContent />
    </Suspense>
  );
}
