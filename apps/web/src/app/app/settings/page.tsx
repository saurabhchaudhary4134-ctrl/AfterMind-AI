"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/providers/auth-context";
import { useToast } from "@/components/ui/toast";
import { authApi } from "@/lib/api/endpoints";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export default function SettingsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [fullName, setFullName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) setFullName(user.full_name);
  }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await authApi.updateMe({ full_name: fullName });
      toast("Profile updated", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to update", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-8">Settings</h1>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Update your personal information.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Full Name</Label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={user?.email || ""} disabled />
            <p className="text-xs text-slate-500 mt-1">Email cannot be changed.</p>
          </div>
          <Button onClick={handleSave} loading={saving}>Save Changes</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Workspace Settings</CardTitle>
          <CardDescription>Manage workspace members and permissions.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-400">
            Workspace member management is available via the API. A full UI for member
            management will be added in a future update.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
