"use client";

import * as React from "react";
import { History, Trash2, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useActivityLog } from "@/features/analytics/hooks/use-activity-log";
import { clearActivityLog } from "@/features/analytics/activity-log";

const MAX_ROWS = 20;

export function RecentActivityTable() {
  const entries = useActivityLog();
  const [confirmClear, setConfirmClear] = React.useState(false);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-1.5">
            <History className="h-3.5 w-3.5" /> Recent activity
          </CardTitle>
          <CardDescription>Most recent {MAX_ROWS} logged actions in this browser.</CardDescription>
        </div>
        {entries.length > 0 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => setConfirmClear(true)}
          >
            <Trash2 /> Clear log
          </Button>
        )}
      </CardHeader>
      <CardContent className="pt-0">
        {entries.length === 0 ? (
          <EmptyState icon={History} title="Nothing logged yet" className="h-32" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Detail</TableHead>
                <TableHead>Latency</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.slice(0, MAX_ROWS).map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="whitespace-nowrap capitalize">{entry.type}</TableCell>
                  <TableCell className="max-w-[280px] truncate text-muted-foreground">{entry.label}</TableCell>
                  <TableCell className="font-mono text-xs whitespace-nowrap">
                    {entry.latencyMs !== null ? `${entry.latencyMs} ms` : "—"}
                  </TableCell>
                  <TableCell>
                    {entry.success ? (
                      <Badge variant="success" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" /> OK
                      </Badge>
                    ) : (
                      <Badge variant="destructive" className="gap-1">
                        <XCircle className="h-3 w-3" /> Failed
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-right font-mono text-xs text-muted-foreground">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <ConfirmDialog
        open={confirmClear}
        onOpenChange={setConfirmClear}
        title="Clear activity log?"
        description="Removes locally recorded activity from this browser. This can't be undone."
        confirmLabel="Clear log"
        confirmVariant="destructive"
        onConfirm={() => {
          clearActivityLog();
          setConfirmClear(false);
          toast.success("Activity log cleared");
        }}
      />
    </Card>
  );
}
