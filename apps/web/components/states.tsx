import { Activity, AlertCircle, Compass } from "lucide-react";
import Link from "next/link";
import { Button } from "./ui/button";
export function Loading() {
  return (
    <div aria-label="Loading data" role="status" className="skeleton-group">
      <div className="skeleton h-24" />
      <div className="skeleton h-48" />
      <span className="sr-only">Loading CodePulse data</span>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error;
  retry?: () => void;
}) {
  return (
    <div className="state-box" role="alert">
      <AlertCircle size={28} />
      <h3>Unable to load data</h3>
      <p>{error.message}</p>
      {retry && (
        <Button variant="outline" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}
export function Empty({
  title = "Your next discovery starts here",
  description = "No repositories match these filters. Try a broader search, or check ingestion settings.",
  settings = false,
}: {
  title?: string;
  description?: string;
  settings?: boolean;
}) {
  return (
    <div className="state-box">
      <span className="state-icon">
        <Compass size={26} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {settings && (
        <Button asChild variant="outline">
          <Link href="/settings">
            <Activity size={14} /> Ingestion settings
          </Link>
        </Button>
      )}
    </div>
  );
}
