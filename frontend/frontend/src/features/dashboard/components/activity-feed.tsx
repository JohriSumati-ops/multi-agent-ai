"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { FileText, Activity } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { DOCUMENT_STATUS_LABEL, DOCUMENT_STATUS_VARIANT } from "@/features/documents/status";
import { fadeInUp, reducedMotionVariants, staggerChildren } from "@/lib/motion";

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function ActivityFeed() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5" /> Recent activity
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Activity feed">
          <FeedBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function FeedBody() {
  const { data: documents, isLoading } = useDocuments();
  const reduceMotion = useReducedMotion();

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  const events = [...(documents ?? [])]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 8);

  if (events.length === 0) {
    return <EmptyState icon={FileText} title="No activity yet" description="Upload a document to get started." />;
  }

  const variants = reduceMotion ? reducedMotionVariants : staggerChildren();
  const itemVariants = reduceMotion ? reducedMotionVariants : fadeInUp;

  return (
    <motion.ul initial="hidden" animate="visible" variants={variants} className="space-y-1">
      {events.map((doc) => (
        <motion.li
          key={doc.id}
          variants={itemVariants}
          className="flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors hover:bg-muted/50"
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate text-foreground">{doc.title}</span>
          <Badge variant={DOCUMENT_STATUS_VARIANT[doc.status]}>{DOCUMENT_STATUS_LABEL[doc.status]}</Badge>
          <span className="w-14 shrink-0 text-right text-[11px] text-muted-foreground">
            {relativeTime(doc.updated_at)}
          </span>
        </motion.li>
      ))}
    </motion.ul>
  );
}